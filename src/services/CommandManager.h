//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef COMMANDMANAGER_H
#define COMMANDMANAGER_H

#include <thread>

#include "MongooseHttpServer.h"
#include "UdpServer.h"

#define HTTP_PORT 80

class CommandManager {
public:
    void init();
    void start_async();
    void stop();

    static void process_command(const Command &command);

private:
    // UdpServer udp_server;
    MongooseHttpServer server;
    bool stopped = false;
    TaskHandle_t xHandle = nullptr;
};



#endif //COMMANDMANAGER_H
