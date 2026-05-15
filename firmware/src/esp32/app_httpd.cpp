/*
 * @Date: 2022-1-27 11:45:09
 * @Description: ESP32 Camera Surveillance Car
 * @FilePath:
 */
#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_camera.h"
#include "img_converters.h"
#include "camera_index.h"
#include "Arduino.h"

extern int gpLed;
extern String WiFiAddr;
byte txdata[3] = {0xA5, 0, 0x5A};
const int Forward       = 92;                               // 前进
const int Backward      = 163;                              // 后退
const int Turn_Left     = 149;                              // 左平移
const int Turn_Right    = 106;                              // 右平移
const int Top_Left      = 20;                               // 左上移动
const int Bottom_Left   = 129;                              // 左下移动
const int Top_Right     = 72;                               // 右上移动
const int Bottom_Right  = 34;                               // 右下移动
const int Stop          = 0;                                // 停止
// const int Contrarotate  = 172;                              // 逆时针旋转
const int Clockwise     = 83;                               // 顺时针旋转
const int Moedl1        = 25;                               // 模式1
const int Moedl2        = 26;                               // 模式2
const int Moedl3        = 27;                               // 模式3
const int Moedl4        = 28;                               // 模式4
const int MotorLeft     = 230;                              // 舵机左转
const int MotorRight    = 231;                              // 舵机右转

#define HTTPD_DEFAULT_CONFIG_demo() {                        \
        .task_priority      = tskIDLE_PRIORITY+5,       \
        .stack_size         = 8192,                     \
        .server_port        = 80,                       \
        .ctrl_port          = 32768,                    \
        .max_open_sockets   = 7,                        \
        .max_uri_handlers   = 19,                        \
        .max_resp_headers   = 19,                        \
        .backlog_conn       = 5,                        \
        .lru_purge_enable   = false,                    \
        .recv_wait_timeout  = 5,                        \
        .send_wait_timeout  = 5,                        \
        .global_user_ctx = NULL,                        \
        .global_user_ctx_free_fn = NULL,                \
        .global_transport_ctx = NULL,                   \
        .global_transport_ctx_free_fn = NULL,           \
        .open_fn = NULL,                                \
        .close_fn = NULL,                               \
        .uri_match_fn = NULL                            \
}

typedef struct
{
    size_t size;  // number of values used for filtering
    size_t index; // current value index
    size_t count; // value count
    int sum;
    int *values; // array to be filled with values
} ra_filter_t;

typedef struct
{
    httpd_req_t *req;
    size_t len;
} jpg_chunking_t;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char *_STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *_STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char *_STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static ra_filter_t ra_filter;
httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL;

static ra_filter_t *ra_filter_init(ra_filter_t *filter, size_t sample_size)
{
    memset(filter, 0, sizeof(ra_filter_t));

    filter->values = (int *)malloc(sample_size * sizeof(int));
    if (!filter->values)
    {
        return NULL;
    }
    memset(filter->values, 0, sample_size * sizeof(int));

    filter->size = sample_size;
    return filter;
}

static int ra_filter_run(ra_filter_t *filter, int value)
{
    if (!filter->values)
    {
        return value;
    }
    filter->sum -= filter->values[filter->index];
    filter->values[filter->index] = value;
    filter->sum += filter->values[filter->index];
    filter->index++;
    filter->index = filter->index % filter->size;
    if (filter->count < filter->size)
    {
        filter->count++;
    }
    return filter->sum / filter->count;
}

static size_t jpg_encode_stream(void *arg, size_t index, const void *data, size_t len)
{
    jpg_chunking_t *j = (jpg_chunking_t *)arg;
    if (!index)
    {
        j->len = 0;
    }
    if (httpd_resp_send_chunk(j->req, (const char *)data, len) != ESP_OK)
    {
        return 0;
    }
    j->len += len;
    return len;
}

static esp_err_t capture_handler(httpd_req_t *req)
{
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    int64_t fr_start = esp_timer_get_time();

    fb = esp_camera_fb_get();
    if (!fb)
    {
        Serial.printf("Camera capture failed");
        httpd_resp_send_500(req);

        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");

    size_t fb_len = 0;
    if (fb->format == PIXFORMAT_JPEG)
    {
        fb_len = fb->len;
        res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
    }
    else
    {
        jpg_chunking_t jchunk = {req, 0};
        res = frame2jpg_cb(fb, 80, jpg_encode_stream, &jchunk) ? ESP_OK : ESP_FAIL;
        httpd_resp_send_chunk(req, NULL, 0);
        fb_len = jchunk.len;
    }
    esp_camera_fb_return(fb);
    int64_t fr_end = esp_timer_get_time();
    Serial.printf("JPG: %uB %ums", (uint32_t)(fb_len), (uint32_t)((fr_end - fr_start) / 1000));
    return res;
}

static esp_err_t stream_handler(httpd_req_t *req)
{
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t *_jpg_buf = NULL;
    char *part_buf[64];

    static int64_t last_frame = 0;
    if (!last_frame)
    {
        last_frame = esp_timer_get_time();
    }

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK)
    {
        return res;
    }

    while (true)
    {
        fb = esp_camera_fb_get();
        if (!fb)
        {
            Serial.printf("Camera capture failed");
            res = ESP_FAIL;
        }
        else
        {
            if (fb->format != PIXFORMAT_JPEG)
            {
                bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
                esp_camera_fb_return(fb);
                fb = NULL;
                if (!jpeg_converted)
                {
                    Serial.printf("JPEG compression failed");
                    res = ESP_FAIL;
                }
            }
            else
            {
                _jpg_buf_len = fb->len;
                _jpg_buf = fb->buf;
            }
        }
        if (res == ESP_OK)
        {
            size_t hlen = snprintf((char *)part_buf, 64, _STREAM_PART, _jpg_buf_len);
            res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
        }
        if (res == ESP_OK)
        {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }
        if (res == ESP_OK)
        {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }
        if (fb)
        {
            esp_camera_fb_return(fb);
            fb = NULL;
            _jpg_buf = NULL;
        }
        else if (_jpg_buf)
        {
            free(_jpg_buf);
            _jpg_buf = NULL;
        }
        if (res != ESP_OK)
        {
            break;
        }
        int64_t fr_end = esp_timer_get_time();

        int64_t frame_time = fr_end - last_frame;
        last_frame = fr_end;
        frame_time /= 1000;
        uint32_t avg_frame_time = ra_filter_run(&ra_filter, frame_time);
    }

    last_frame = 0;
    return res;
}

static esp_err_t cmd_handler(httpd_req_t *req)
{
    char *buf;
    size_t buf_len;
    char variable[32] = {
        0,
    };
    char value[32] = {
        0,
    };

    buf_len = httpd_req_get_url_query_len(req) + 1;
    if (buf_len > 1)
    {
        buf = (char *)malloc(buf_len);
        if (!buf)
        {
            httpd_resp_send_500(req);
            return ESP_FAIL;
        }
        if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK)
        {
            if (httpd_query_key_value(buf, "var", variable, sizeof(variable)) == ESP_OK &&
                httpd_query_key_value(buf, "val", value, sizeof(value)) == ESP_OK)
            {
            }
            else
            {
                free(buf);
                httpd_resp_send_404(req);
                return ESP_FAIL;
            }
        }
        else
        {
            free(buf);
            httpd_resp_send_404(req);
            return ESP_FAIL;
        }
        free(buf);
    }
    else
    {
        httpd_resp_send_404(req);
        return ESP_FAIL;
    }

    int val = atoi(value);
    sensor_t *s = esp_camera_sensor_get();
    int res = 0;

    if (!strcmp(variable, "framesize"))
    {
        if (s->pixformat == PIXFORMAT_JPEG)
            res = s->set_framesize(s, (framesize_t)val);
    }
    else if (!strcmp(variable, "quality"))
        res = s->set_quality(s, val);
    else if (!strcmp(variable, "contrast"))
        res = s->set_contrast(s, val);
    else if (!strcmp(variable, "brightness"))
        res = s->set_brightness(s, val);
    else if (!strcmp(variable, "saturation"))
        res = s->set_saturation(s, val);
    else if (!strcmp(variable, "gainceiling"))
        res = s->set_gainceiling(s, (gainceiling_t)val);
    else if (!strcmp(variable, "colorbar"))
        res = s->set_colorbar(s, val);
    else if (!strcmp(variable, "awb"))
        res = s->set_whitebal(s, val);
    else if (!strcmp(variable, "agc"))
        res = s->set_gain_ctrl(s, val);
    else if (!strcmp(variable, "aec"))
        res = s->set_exposure_ctrl(s, val);
    else if (!strcmp(variable, "hmirror"))
        res = s->set_hmirror(s, val);
    else if (!strcmp(variable, "vflip"))
        res = s->set_vflip(s, val);
    else if (!strcmp(variable, "awb_gain"))
        res = s->set_awb_gain(s, val);
    else if (!strcmp(variable, "agc_gain"))
        res = s->set_agc_gain(s, val);
    else if (!strcmp(variable, "aec_value"))
        res = s->set_aec_value(s, val);
    else if (!strcmp(variable, "aec2"))
        res = s->set_aec2(s, val);
    else if (!strcmp(variable, "dcw"))
        res = s->set_dcw(s, val);
    else if (!strcmp(variable, "bpc"))
        res = s->set_bpc(s, val);
    else if (!strcmp(variable, "wpc"))
        res = s->set_wpc(s, val);
    else if (!strcmp(variable, "raw_gma"))
        res = s->set_raw_gma(s, val);
    else if (!strcmp(variable, "lenc"))
        res = s->set_lenc(s, val);
    else if (!strcmp(variable, "special_effect"))
        res = s->set_special_effect(s, val);
    else if (!strcmp(variable, "wb_mode"))
        res = s->set_wb_mode(s, val);
    else if (!strcmp(variable, "ae_level"))
        res = s->set_ae_level(s, val);
    else
    {
        res = -1;
    }

    if (res)
    {
        return httpd_resp_send_500(req);
    }

    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, NULL, 0);
}



static esp_err_t status_handler(httpd_req_t *req)
{
    static char json_response[1024];

    sensor_t *s = esp_camera_sensor_get();
    char *p = json_response;
    *p++ = '{';

    p += sprintf(p, "\"framesize\":%u,", s->status.framesize);
    p += sprintf(p, "\"quality\":%u,", s->status.quality);
    p += sprintf(p, "\"brightness\":%d,", s->status.brightness);
    p += sprintf(p, "\"contrast\":%d,", s->status.contrast);
    p += sprintf(p, "\"saturation\":%d,", s->status.saturation);
    p += sprintf(p, "\"special_effect\":%u,", s->status.special_effect);
    p += sprintf(p, "\"wb_mode\":%u,", s->status.wb_mode);
    p += sprintf(p, "\"awb\":%u,", s->status.awb);
    p += sprintf(p, "\"awb_gain\":%u,", s->status.awb_gain);
    p += sprintf(p, "\"aec\":%u,", s->status.aec);
    p += sprintf(p, "\"aec2\":%u,", s->status.aec2);
    p += sprintf(p, "\"ae_level\":%d,", s->status.ae_level);
    p += sprintf(p, "\"aec_value\":%u,", s->status.aec_value);
    p += sprintf(p, "\"agc\":%u,", s->status.agc);
    p += sprintf(p, "\"agc_gain\":%u,", s->status.agc_gain);
    p += sprintf(p, "\"gainceiling\":%u,", s->status.gainceiling);
    p += sprintf(p, "\"bpc\":%u,", s->status.bpc);
    p += sprintf(p, "\"wpc\":%u,", s->status.wpc);
    p += sprintf(p, "\"raw_gma\":%u,", s->status.raw_gma);
    p += sprintf(p, "\"lenc\":%u,", s->status.lenc);
    p += sprintf(p, "\"hmirror\":%u,", s->status.hmirror);
    p += sprintf(p, "\"dcw\":%u,", s->status.dcw);
    p += sprintf(p, "\"colorbar\":%u", s->status.colorbar);
    *p++ = '}';
    *p++ = 0;
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, json_response, strlen(json_response));
}

static esp_err_t index_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    String page = "";
    page += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0\">\n";
    page += "<script>var xhttp = new XMLHttpRequest();</script>";
    page += "<script>function getsend(arg) { xhttp.open('GET', arg +'?' + new Date().getTime(), true); xhttp.send() } </script>";
    page += "<p align=center><IMG SRC='http://" + WiFiAddr + ":81/stream' style='width:280px;transform:rotate(0deg);'></p><br/><br/>";

    // page += "<p align=center>";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('leftup') onmouseup=getsend('stop') ontouchstart=getsend('leftup') ontouchend=getsend('stop')><b>LeftUp</b></button>&nbsp;";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('go') onmouseup=getsend('stop') ontouchstart=getsend('go') ontouchend=getsend('stop') ><b>Forward</b></button>&nbsp;";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('rightup') onmouseup=getsend('stop') ontouchstart=getsend('rightup') ontouchend=getsend('stop') ><b>RightUp</b></button>";
    // page += "</p>";

    // page += "<p align=center>";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px; onmousedown=getsend('left') onmouseup=getsend('stop') ontouchstart=getsend('left') ontouchend=getsend('stop')><b>Left</b></button>&nbsp;";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px; onmousedown=getsend('clockwise') onmouseup=getsend('stop') ontouchstart=getsend('clockwise') ontouchend=getsend('stop')><b>Clockwise</b></button>&nbsp;";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('right') onmouseup=getsend('stop') ontouchstart=getsend('right') ontouchend=getsend('stop')><b>Right</b></button>";
    // page += "</p>";

    // page += "<p align=center>";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px;onmousedown=getsend('leftdown') onmouseup=getsend('stop') ontouchstart=getsend('leftdown') ontouchend=getsend('stop') ><b>LeftDown</b></button>&nbsp;";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('back') onmouseup=getsend('stop') ontouchstart=getsend('back') ontouchend=getsend('stop') ><b>Backward</b></button>&nbsp;";
    // page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('rightdown') onmouseup=getsend('stop') ontouchstart=getsend('rightdown') ontouchend=getsend('stop') ><b>RightDown</b></button>";
    // page += "</p>";
    page += "<p align=center>";
    page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('leftup') onmouseup=getsend('stop') ontouchstart=getsend('leftup') ontouchend=getsend('stop')><b>LeftUp</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('go') onmouseup=getsend('stop') ontouchstart=getsend('go') ontouchend=getsend('stop') ><b>Forward</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('rightup') onmouseup=getsend('stop') ontouchstart=getsend('rightup') ontouchend=getsend('stop') ><b>RightUp</b></button>";
    page += "</p>";

    page += "<p align=center>";
    page += "<button style=background-color:lightgrey;width:90px;height:40px; onmousedown=getsend('left') onmouseup=getsend('stop') ontouchstart=getsend('left') ontouchend=getsend('stop')><b>Left</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:90px;height:40px; onmousedown=getsend('clockwise') onmouseup=getsend('stop') ontouchstart=getsend('clockwise') ontouchend=getsend('stop')><b>Clockwise</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:90px;height:40px; onmousedown=getsend('right') onmouseup=getsend('stop') ontouchstart=getsend('right') ontouchend=getsend('stop')><b>Right</b></button>";
    page += "</p>";

    page += "<p align=center>";
    page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('leftdown') onmouseup=getsend('stop') ontouchstart=getsend('leftdown') ontouchend=getsend('stop') ><b>LeftDown</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('back') onmouseup=getsend('stop') ontouchstart=getsend('back') ontouchend=getsend('stop') ><b>Backward</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:90px;height:40px onmousedown=getsend('rightdown') onmouseup=getsend('stop') ontouchstart=getsend('rightdown') ontouchend=getsend('stop') ><b>RightDown</b></button>";
    page += "</p>";

    page += "<p align=center>";
    page += "<button style=background-color:lightgrey;width:120px;height:40px;onmousedown=getsend('model1') onmouseup=getsend('model1') ontouchstart=getsend('model1') ontouchend=getsend('model1') ><b>model1</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:120px;height:40px onmousedown=getsend('model2') onmouseup=getsend('model2') ontouchstart=getsend('model2') ontouchend=getsend('model2') ><b>model2</b></button>";
    page += "</p>";

    page += "<p align=center>";
    page += "<button style=background-color:lightgrey;width:120px;height:40px;onmousedown=getsend('model3') onmouseup=getsend('model3') ontouchstart=getsend('model3') ontouchend=getsend('model3') ><b>model3</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:120px;height:40px onmousedown=getsend('model4') onmouseup=getsend('model4') ontouchstart=getsend('model4') ontouchend=getsend('model4') ><b>model4</b></button>";
    page += "</p>";

    page += "<p align=center>";
    page += "<button style=background-color:lightgrey;width:120px;height:40px onmousedown=getsend('motorleft') onmouseup=getsend('stop') ontouchstart=getsend('motorleft') ontouchend=getsend('stop') ><b>MotorLeft</b></button>&nbsp;";
    page += "<button style=background-color:lightgrey;width:120px;height:40px onmousedown=getsend('motorright') onmouseup=getsend('stop') ontouchstart=getsend('motorright') ontouchend=getsend('stop') ><b>MotorRight</b></button>";
    page += "</p>";

    page += "<p align=center>";
    page += "<button style=background-color:yellow;width:100px;height:40px onmousedown=getsend('ledon')><b>Light ON</b></button>&nbsp;";
    page += "<button style=background-color:indianred;width:100px;height:40px onmousedown=getsend('stop') onmouseup=getsend('stop')><b>Stop</b></button>&nbsp;";
    page += "<button style=background-color:yellow;width:100px;height:40px onmousedown=getsend('ledoff')><b>Light OFF</b></button>";
    page += "</p>";

    return httpd_resp_send(req, &page[0], strlen(&page[0]));
}

/* URI 处理函数*/
static esp_err_t go_handler(httpd_req_t *req)
{
    txdata[1] = Forward;
    Serial.write(txdata, 3);
    Serial.println("Go");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t back_handler(httpd_req_t *req)
{
    txdata[1] = Backward;
    Serial.write(txdata, 3);
    Serial.println("Back");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t left_handler(httpd_req_t *req)
{
    txdata[1] = Turn_Left;
    Serial.write(txdata, 3);
    Serial.println("Left");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t right_handler(httpd_req_t *req)
{
    txdata[1] = Turn_Right;
    Serial.write(txdata, 3);
    Serial.println("Right");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t stop_handler(httpd_req_t *req)
{
    txdata[1] = Stop;
    Serial.write(txdata, 3);
    Serial.println("Stop");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t ledon_handler(httpd_req_t *req)
{
    digitalWrite(gpLed, HIGH);
    Serial.println("LED ON");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t ledoff_handler(httpd_req_t *req)
{
    digitalWrite(gpLed, LOW);
    Serial.println("LED OFF");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}

//////////////////////////////new/////////////////////////////////
static esp_err_t leftup_handler(httpd_req_t *req)           // 左上
{
    txdata[1] = Top_Left;
    Serial.write(txdata, 3);
    Serial.println("leftup");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t leftdown_handler(httpd_req_t *req)         // 左下
{
    txdata[1] = Bottom_Left;
    Serial.write(txdata, 3);
    Serial.println("leftdown");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t rightup_handler(httpd_req_t *req)          // 右上
{
    txdata[1] = Top_Right;
    Serial.write(txdata, 3);
    Serial.println("rightup");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t rightdown_handler(httpd_req_t *req)        // 右下
{
    txdata[1] = Bottom_Right;
    Serial.write(txdata, 3);
    Serial.println("rightdown");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t clockwise_handler(httpd_req_t *req)        // 顺时针原地旋转
{
    txdata[1] = Clockwise;
    Serial.write(txdata, 3);
    Serial.println("clockwise");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t model1_handler(httpd_req_t *req)           // 模式1 自由模式
{
    txdata[1] = Moedl1;
    Serial.write(txdata, 3);
    Serial.println("model1");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t model2_handler(httpd_req_t *req)           // 模式2 避障模式
{
    txdata[1] = Moedl2;
    Serial.write(txdata, 3);
    Serial.println("model2");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t model3_handler(httpd_req_t *req)           // 模式3 跟随模式
{
    txdata[1] = Moedl3;
    Serial.write(txdata, 3);
    Serial.println("model3");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t model4_handler(httpd_req_t *req)           // 模式4 巡线模式
{
    txdata[1] = Moedl4;
    Serial.write(txdata, 3);
    Serial.println("model4");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t motorleft_handler(httpd_req_t *req)           // 舵机左转
{
    txdata[1] = MotorLeft;
    Serial.write(txdata, 3);
    Serial.println("MotorLeft");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
static esp_err_t motorright_handler(httpd_req_t *req)           // 舵机右转
{
    txdata[1] = MotorRight;
    Serial.write(txdata, 3);
    Serial.println("MotorRight");
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, "OK", 2);
}
//////////////////////////////new/////////////////////////////////

void startCameraServer()
{
    uint32_t i;
    httpd_config_t config = HTTPD_DEFAULT_CONFIG_demo();

    httpd_uri_t go_uri = {
        .uri = "/go",
        .method = HTTP_GET,
        .handler = go_handler,
        .user_ctx = NULL};

    httpd_uri_t back_uri = {
        .uri = "/back",
        .method = HTTP_GET,
        .handler = back_handler,
        .user_ctx = NULL};

    httpd_uri_t stop_uri = {
        .uri = "/stop",
        .method = HTTP_GET,
        .handler = stop_handler,
        .user_ctx = NULL};

    httpd_uri_t left_uri = {
        .uri = "/left",
        .method = HTTP_GET,
        .handler = left_handler,
        .user_ctx = NULL};

    httpd_uri_t right_uri = {
        .uri = "/right",
        .method = HTTP_GET,
        .handler = right_handler,
        .user_ctx = NULL};

//////////////////////////////new/////////////////////////////////
    httpd_uri_t leftup_uri = {              // 左上
        .uri = "/leftup",
        .method = HTTP_GET,
        .handler = leftup_handler,
        .user_ctx = NULL};

    httpd_uri_t leftdown_uri = {            // 左下
        .uri = "/leftdown",
        .method = HTTP_GET,
        .handler = leftdown_handler,
        .user_ctx = NULL};

    httpd_uri_t rightup_uri = {             // 右上
        .uri = "/rightup",
        .method = HTTP_GET,
        .handler = rightup_handler,
        .user_ctx = NULL};

    httpd_uri_t rightdown_uri = {           // 右下
        .uri = "/rightdown",
        .method = HTTP_GET,
        .handler = rightdown_handler,
        .user_ctx = NULL};

    httpd_uri_t clockwise_uri = {           // 顺时针原地旋转
        .uri = "/clockwise",
        .method = HTTP_GET,
        .handler = clockwise_handler,       
        .user_ctx = NULL};

    httpd_uri_t model1_uri = {              // 模式1
        .uri = "/model1",
        .method = HTTP_GET,
        .handler = model1_handler,
        .user_ctx = NULL};

    httpd_uri_t model2_uri = {              // 模式2
        .uri = "/model2",
        .method = HTTP_GET,
        .handler = model2_handler,
        .user_ctx = NULL};

    httpd_uri_t model3_uri = {              // 模式3
        .uri = "/model3",
        .method = HTTP_GET,
        .handler = model3_handler,
        .user_ctx = NULL};
    httpd_uri_t model4_uri = {              // 模式4
        .uri = "/model4",
        .method = HTTP_GET,
        .handler = model4_handler,
        .user_ctx = NULL};
    httpd_uri_t motorleft_uri = {              // 舵机左转
        .uri = "/motorleft",
        .method = HTTP_GET,
        .handler = motorleft_handler,
        .user_ctx = NULL};
    httpd_uri_t motorright_uri = {              // 舵机右转
        .uri = "/motorright",
        .method = HTTP_GET,
        .handler = motorright_handler,
        .user_ctx = NULL};
//////////////////////////////new/////////////////////////////////

    httpd_uri_t ledon_uri = {
        .uri = "/ledon",
        .method = HTTP_GET,
        .handler = ledon_handler,
        .user_ctx = NULL};

    httpd_uri_t ledoff_uri = {
        .uri = "/ledoff",
        .method = HTTP_GET,
        .handler = ledoff_handler,
        .user_ctx = NULL};

    httpd_uri_t index_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = index_handler,
        .user_ctx = NULL};

    httpd_uri_t status_uri = {
        .uri = "/status",
        .method = HTTP_GET,
        .handler = status_handler,
        .user_ctx = NULL};

    httpd_uri_t cmd_uri = {
        .uri = "/control",
        .method = HTTP_GET,
        .handler = cmd_handler,
        .user_ctx = NULL};

    httpd_uri_t capture_uri = {
        .uri = "/capture",
        .method = HTTP_GET,
        .handler = capture_handler,
        .user_ctx = NULL};

    httpd_uri_t stream_uri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL};

    ra_filter_init(&ra_filter, 20);
    Serial.printf("Starting web server on port: '%d'", config.server_port);

    /* 启动 httpd server */
    if (httpd_start(&camera_httpd, &config) == ESP_OK)
    {
        /* 注册 URI 处理程序 */
        httpd_register_uri_handler(camera_httpd, &index_uri);
        httpd_register_uri_handler(camera_httpd, &go_uri);
        httpd_register_uri_handler(camera_httpd, &back_uri);
        httpd_register_uri_handler(camera_httpd, &stop_uri);
        httpd_register_uri_handler(camera_httpd, &left_uri);
        httpd_register_uri_handler(camera_httpd, &right_uri);
        httpd_register_uri_handler(camera_httpd, &ledon_uri);
        httpd_register_uri_handler(camera_httpd, &ledoff_uri);
        //////////////////////////////new/////////////////////////////////
        httpd_register_uri_handler(camera_httpd, &leftup_uri);
        httpd_register_uri_handler(camera_httpd, &leftdown_uri);
        httpd_register_uri_handler(camera_httpd, &rightup_uri);
        httpd_register_uri_handler(camera_httpd, &rightdown_uri);
        httpd_register_uri_handler(camera_httpd, &clockwise_uri);
        httpd_register_uri_handler(camera_httpd, &model1_uri);
        httpd_register_uri_handler(camera_httpd, &model2_uri);
        httpd_register_uri_handler(camera_httpd, &model3_uri);
        httpd_register_uri_handler(camera_httpd, &model4_uri);
        httpd_register_uri_handler(camera_httpd, &motorleft_uri);
        httpd_register_uri_handler(camera_httpd, &motorright_uri);
        //////////////////////////////new/////////////////////////////////
    }

    config.server_port += 1;
    config.ctrl_port += 1;
    Serial.printf("Starting stream server on port: '%d'", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK)
    {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
    }
}
