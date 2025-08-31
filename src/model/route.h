//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef ROUTE_H
#define ROUTE_H
#include <memory>

#include "ICanBeDeserialized.h"
#include "MongooseHttp.h"
#include "MongooseHttpServer.h"
#include "utils/pointer.h"


class IRequestFactory {
public:
    virtual ~IRequestFactory() = default;
    virtual std::unique_ptr<ICanBeDeserialized> createRequest() const = 0;
};

// Specify the request class as a template parameter
template <typename T>
class RequestFactory final : public IRequestFactory {
public:
    RequestFactory() {
        // Ensure T inherits from ICanBeDeserialized at compile time
        static_assert(std::is_base_of<ICanBeDeserialized, T>::value, "Error: Type T must inherit from ICanBeDeserialized.");
    };

    std::unique_ptr<ICanBeDeserialized> createRequest() const override {
        return make_unique<T>();
    }
};

class  Route {
public:
    Route(
        const HttpRequestMethod http_method,
        std::shared_ptr<ICanBeDeserialized>(*from_json)(const char *json_str, DeserializationError &error, String &error_msg),
        void(*handler)(MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized> &command))
        : _http_method(http_method),
          _from_json(from_json),
          _handler(handler) { }

    HttpRequestMethod getHttpMethod() const { return _http_method; }

    std::shared_ptr<ICanBeDeserialized> fromJson(const char *json_str, DeserializationError &error, String &error_msg) const;
    void handler(MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized> &command) const;

private:
    // The HTTP method for this route (GET, POST, etc.)
    HttpRequestMethod _http_method;
    // A factory to create the associated response object
    std::shared_ptr<ICanBeDeserialized> (*_from_json)(const char *json_str, DeserializationError& error, String &error_msg);
    // The handler function to be called when this route is accessed
    void (*_handler)(MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command);
};



#endif //ROUTE_H
