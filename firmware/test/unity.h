// Minimal Unity test framework header for native testing
#ifndef UNITY_H
#define UNITY_H

#include <cstdio>
#include <cstdlib>

static int _unity_test_count = 0;
static int _unity_pass_count = 0;
static int _unity_fail_count = 0;
static const char* _unity_current_test = nullptr;

#define TEST_ASSERT_TRUE(condition) do { \
    if (!(condition)) { \
        printf("FAIL: %s line %d: expected TRUE\n", _unity_current_test, __LINE__); \
        _unity_fail_count++; \
        return; \
    } \
    _unity_pass_count++; \
} while(0)

#define TEST_ASSERT_FALSE(condition) TEST_ASSERT_TRUE(!(condition))

#define TEST_ASSERT_EQUAL(expected, actual) do { \
    if ((expected) != (actual)) { \
        printf("FAIL: %s line %d: expected %d, got %d\n", _unity_current_test, __LINE__, (int)(expected), (int)(actual)); \
        _unity_fail_count++; \
        return; \
    } \
    _unity_pass_count++; \
} while(0)

#define TEST_ASSERT_EQUAL_STRING(expected, actual) do { \
    if (strcmp(expected, actual) != 0) { \
        printf("FAIL: %s line %d: expected \"%s\", got \"%s\"\n", _unity_current_test, __LINE__, expected, actual); \
        _unity_fail_count++; \
        return; \
    } \
    _unity_pass_count++; \
} while(0)

#define RUN_TEST(func) do { \
    _unity_current_test = #func; \
    _unity_test_count++; \
    setUp(); \
    func(); \
    tearDown(); \
    printf("PASS: %s\n", #func); \
} while(0)

#define UNITY_BEGIN() do { \
    _unity_test_count = 0; \
    _unity_pass_count = 0; \
    _unity_fail_count = 0; \
    printf("┌─────────────────────────────────┐\n"); \
    printf("│  SMART SPRINKLER FIRMWARE TESTS │\n"); \
    printf("└─────────────────────────────────┘\n\n"); \
} while(0)

#define UNITY_END() do { \
    printf("\n───────────────────────────────────\n"); \
    printf("Results: %d tests, %d passed, %d failed\n", \
           _unity_test_count, _unity_pass_count, _unity_fail_count); \
    return _unity_fail_count > 0 ? 1 : 0; \
} while(0)

#endif // UNITY_H
