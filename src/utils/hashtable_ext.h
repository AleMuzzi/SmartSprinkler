//
// Created by Alessandro Muzzi on 09/09/25.
//

#ifndef HASHTABLE_EXT_H
#define HASHTABLE_EXT_H

#include <Hashtable.h>

static String field_to_string(const String& str) {
    return "\"" + str + "\"";
}

// Define Lambda expression type that takes and returns a reference to the object.
template <typename K, typename V, typename Hash = KeyHash<K>>
static String hashtable_to_string(
    const Hashtable<K, V, Hash>& ht,
    String (*keyToString)(const K&) = nullptr,
    String (*valueToString)(const V&) = nullptr
    ) {
    String result = "{";

    if (keyToString == nullptr) {
        keyToString = field_to_string;
    }
    if (valueToString == nullptr) {
        valueToString = field_to_string;
    }

    for (const auto &key : ht.keys()) {
        const auto value = ht.get(key);
        result += keyToString(key) + ": " + valueToString(*value) + ", ";
    }
    if (result.length() > 1) {
        result.remove(result.length() - 2); // Remove trailing comma and space
    }
    result += "}";
    return result;
}



#endif //HASHTABLE_EXT_H
