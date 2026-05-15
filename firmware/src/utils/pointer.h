//
// Created by Alessandro Muzzi on 24/08/25.
//

#ifndef POINTER_H
#define POINTER_H
#include <memory>


template<typename T, typename... Args>
std::unique_ptr<T> make_unique(Args&&... args) {
    return std::unique_ptr<T>(new T(std::forward<Args>(args)...));
}




#endif //POINTER_H
