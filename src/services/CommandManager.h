//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef COMMANDMANAGER_H
#define COMMANDMANAGER_H


#include "MongooseHttpServer.h"
#include "UdpServer.h"

#define HTTP_PORT 80

class CommandManager {
public:
    void init();
    void poll();

private:
    // UdpServer udp_server;
    MongooseHttpServer server;
    bool stopped = false;
    TaskHandle_t xHandle = nullptr;

    void setup_routes();

    static void process_command(const Command &command);
};


#endif //COMMANDMANAGER_H
