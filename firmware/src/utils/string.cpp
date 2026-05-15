#include "./string.h"

#include <HardwareSerial.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>

char* format(const char* fmt, ...) {
    va_list args;
    int size = 0;
    char *buffer;

    // 1. Initialize va_list
    va_start(args, fmt);

    // 2. Determine the required buffer size using vsnprintf (safe way)
    size = vsnprintf(NULL, 0, fmt, args);

    if (size < 0) {
        va_end(args);
        return NULL; // Error in formatting
    }

    // Allocate memory for the formatted string + 1 for null terminator
    buffer = (char *)malloc(size + 1);
    if (buffer == NULL) {
        va_end(args);
        Serial.println("Malloc failed!");
        return NULL;
    }

    // 3. Format the string into the buffer
    vsnprintf(buffer, size + 1, fmt, args);

    // 4. Clean up va_list
    va_end(args);

    return buffer;
}