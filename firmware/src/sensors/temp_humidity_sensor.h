//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef TEMP_HUMIDITY_SENSOR_H
#define TEMP_HUMIDITY_SENSOR_H


#define DHTPIN 4        // Pin a cui è collegato il sensore
#define DHTTYPE DHT22    // Indicazione del modello del sensore

class TempHumiditySensor {
public:
    static void init();

    static float getTemperature();

    static float getHumidity();

};



#endif //TEMP_HUMIDITY_SENSOR_H
