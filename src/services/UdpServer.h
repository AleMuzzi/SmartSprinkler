//
// Created by Alessandro Muzzi on 25/03/25.
//

#ifndef  UDP_SERVER_H
#define  UDP_SERVER_H

#include <Arduino.h>
#include <lwip/sockets.h>

#include "model/command.h"

#define PORT 12345
#define MAX_BUFFER_SIZE 512

class UdpServer {
public:
    int init(char* &error);
    bool check_for_data(char* buffer);

    // region Getters

    int get_sockfd() const { return this->sockfd; }
    sockaddr_in get_servaddr() const { return this->servaddr; }
    sockaddr_in get_cliaddr() const { return this->cliaddr; }
    socklen_t get_cliaddr_len() const { return this->cliaddr_len; }

    // endregion
private:
    int sockfd;
    sockaddr_in servaddr;
    sockaddr_in cliaddr;
    socklen_t cliaddr_len;

    void process_command(Command command);
};

#endif
