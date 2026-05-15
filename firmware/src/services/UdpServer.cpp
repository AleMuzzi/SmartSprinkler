//
// Created by Alessandro Muzzi on 25/03/25.
//

#include "UdpServer.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include "./utils/string.h"

int UdpServer::init(char* &error) {
    /**
     * Initialize and start the UDP server.
     * Returns the socket file descriptor.
     */

    // Create UDP socket
    Serial.print("Initializing UDP server...");
    Serial.flush();
    if ((this->sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("socket creation failed");
        // put in error the socket error
        error = strerror(errno);
        return -1;
    }

    Serial.println("OK");
    Serial.flush();
    // Set socket to non-blocking mode
    fcntl(this->sockfd, F_SETFL, O_NONBLOCK);
    constexpr int recv_buf_size = MAX_BUFFER_SIZE;
    setsockopt(this->sockfd, SOL_SOCKET, SO_RCVBUF, &recv_buf_size, sizeof(recv_buf_size));

    memset(&servaddr, 0, sizeof(servaddr));
    memset(&cliaddr, 0, sizeof(cliaddr));

    // Fill server information
    servaddr.sin_family = AF_INET; // IPv4
    servaddr.sin_addr.s_addr = INADDR_ANY; // Listen on any interface
    servaddr.sin_port = htons(PORT); // Port number

    Serial.println("OK2");
    Serial.flush();
    // Bind the socket with the server address
    if (bind(this->sockfd, reinterpret_cast<const sockaddr *>(&servaddr), sizeof(servaddr)) < 0) {
        perror("bind failed");
        close(this->sockfd);
        // put in error the socket error
        error = strerror(errno);
        return -1;
    }

    Serial.print(format("UDP server listening on port %d...\n", PORT));

    this->cliaddr_len = sizeof(cliaddr);

    return sockfd;
}

bool UdpServer::check_for_data(char* buffer) {
    const ssize_t n = recvfrom(
        this->sockfd,
        buffer,
        MAX_BUFFER_SIZE,
    MSG_DONTWAIT,
        reinterpret_cast<sockaddr *>(&cliaddr),
        &this->cliaddr_len
        );

    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            // No data available (normal for non-blocking sockets)
            delay(1); // Prevent tight looping
            return false;
        }

        Serial.printf("Fatal error: %d\n", errno);
        perror("recvfrom failed");
        return false;
    }

    return n > 0;
}