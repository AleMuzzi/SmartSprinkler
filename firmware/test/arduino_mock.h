#ifndef ARDUINO_MOCK_H
#define ARDUINO_MOCK_H

#include <cstdint>
#include <cstring>
#include <string>
#include <cstdio>
#include <map>
#include <stdexcept>

typedef uint8_t byte;
typedef uint16_t word;

// Pin state tracking for tests
extern int _mock_pin_modes[40];
extern int _mock_pin_values[40];
extern int _mock_pin_mode_count;

enum PinMode { INPUT, OUTPUT, INPUT_PULLUP };
enum PinState { LOW = 0, HIGH = 1 };

inline void pinMode(uint8_t pin, uint8_t mode) {
    if (pin < 40) {
        _mock_pin_modes[pin] = mode;
        _mock_pin_mode_count++;
    }
}

inline void digitalWrite(uint8_t pin, uint8_t val) {
    if (pin < 40) _mock_pin_values[pin] = val;
}

inline int digitalRead(uint8_t pin) {
    if (pin < 40) return _mock_pin_values[pin];
    return LOW;
}

inline void delay(unsigned long ms) {}

class SerialMock {
public:
    void begin(int) {}
    void print(const char*) {}
    void print(int) {}
    void print(float) {}
    void println(const char*) {}
    void println(int) {}
    void println(float) {}
    void println() {}
    void printf(const char*, ...) {}
    void setDebugOutput(bool) {}
};

extern SerialMock Serial;

// Arduino String class mock
class String {
public:
    String() : data_("") {}
    String(const char* s) : data_(s ? s : "") {}
    String(const std::string& s) : data_(s) {}
    String(int val) : data_(std::to_string(val)) {}
    String(unsigned long val) : data_(std::to_string(val)) {}
    String(float val, int decimals) : data_(std::to_string(val)) {}

    const char* c_str() const { return data_.c_str(); }
    bool operator==(const String& other) const { return data_ == other.data_; }
    bool operator==(const char* other) const { return data_ == other; }
    bool operator!=(const char* other) const { return data_ != other; }
    String operator+(const String& other) const { return String(data_ + other.data_); }
    String operator+(const char* other) const { return String(data_ + other); }
    String& operator=(const char* s) { data_ = s ? s : ""; return *this; }
    bool isEmpty() const { return data_.empty(); }
    int length() const { return static_cast<int>(data_.length()); }
    char charAt(int i) const { return data_[i]; }
    int toInt() const { try { return std::stoi(data_); } catch(...) { return 0; } }
    float toFloat() const { try { return std::stof(data_); } catch(...) { return 0.0f; } }
    void toUpperCase() { for (auto& c : data_) c = toupper(c); }

    std::string data_;
};

int strcmp(const String& a, const String& b) {
    return a.data_.compare(b.data_);
}

// ArduinoJson mock (minimal subset for testing command parsing)
class DeserializationError {
public:
    enum Code {
        Ok,
        InvalidInput,
        NoMemory,
        Empty
    };
    Code code = Ok;
    operator bool() const { return code != Ok; }
    const char* c_str() const {
        switch(code) {
            case Ok: return "Ok";
            case InvalidInput: return "InvalidInput";
            case NoMemory: return "NoMemory";
            case Empty: return "Empty";
        }
        return "Unknown";
    }
    static DeserializationError InvalidInput;
};
inline DeserializationError DeserializationError::InvalidInput = {DeserializationError::InvalidInput};

class JsonDocument {
public:
    class JsonObject {
    public:
        String _value;
        bool _is_int = false;
        int _int_val = 0;
        bool _is_bool = false;
        bool _bool_val = false;
        bool _null = true;

        JsonObject() : _null(true) {}
        JsonObject(const char* v) : _value(v), _null(false) {}
        JsonObject(const String& v) : _value(v), _null(false) {}
        JsonObject(int v) : _is_int(true), _int_val(v), _null(false) {}
        JsonObject(bool v) : _is_bool(true), _bool_val(v), _null(false) {}

        operator String() const { return _value; }
        String as<String>() const { return _value; }
        String asString() const { return _value; }
        int as<int>() const { return _is_int ? _int_val : 0; }
        bool is<int>() const { return _is_int; }
        bool is<bool>() const { return _is_bool; }
        bool isNull() const { return _null; }
    };

    JsonObject operator[](const char* key) const {
        auto it = _values.find(key);
        if (it != _values.end()) return it->second;
        return JsonObject();
    }

    JsonObject operator[](const String& key) const {
        return (*this)[key.c_str()];
    }

    void setValue(const char* key, const JsonObject& val) {
        _values[key] = val;
    }

    std::map<std::string, JsonObject> _values;
};

inline DeserializationError deserializeJson(JsonDocument& doc, const char* json) {
    return DeserializationError();
}

// map and constrain
inline long map(long x, long in_min, long in_max, long out_min, long out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

template<typename T>
inline T constrain(T val, T min, T max) {
    if (val < min) return min;
    if (val > max) return max;
    return val;
}

template<typename T>
inline bool isnan(T val) { return false; }

// WiFi mock
class WiFiClass {
public:
    static const int WL_CONNECTED = 3;
    static const int WIFI_MODE_STA = 1;
    int status_ = WL_CONNECTED;
    void statusReturn(int s) { status_ = s; }
    int status() { return status_; }
    void mode(int) {}
    void begin(const char*, const char*) {}
    void setHostname(const char*) {}
    String macAddress() { return String("00:00:00:00:00:00"); }
    String localIP() { return String("0.0.0.0"); }
};
extern WiFiClass WiFi;

// Timing
extern unsigned long _mock_millis;
unsigned long millis() { return _mock_millis; }

// Hash table placeholder (not used in model tests)
template<typename K, typename V>
class Hashtable {
public:
    void put(K key, V value) { _data[key.data_] = value; }
    V get(K key) { return _data[key.data_]; }
    std::map<std::string, V> _data;
};

template<typename K, typename V>
class HashtableExt : public Hashtable<K, V> {};

#endif // ARDUINO_MOCK_H
