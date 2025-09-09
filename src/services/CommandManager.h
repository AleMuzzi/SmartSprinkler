//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef COMMANDMANAGER_H
#define COMMANDMANAGER_H


#include "MongooseHttpServer.h"

#include <Hashtable.h>
#include "model/route.h"

#define HTTP_PORT 80

class CommandManager {
public:
    void init();
    void poll();
    void setup_routes(const Hashtable<String, Route>& routes);
    bool is_stopped() const { return this->stopped; }

private:
    MongooseHttpServer server;
    bool stopped = false;
    TaskHandle_t xHandle = nullptr;
};


#endif //COMMANDMANAGER_H
