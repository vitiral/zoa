#ifndef __CIV_H
#define __CIV_H
#include <stdint.h>

// #################################
// # Core Types and common methods

typedef uint8_t              U1;
typedef uint16_t             U2;
typedef uint32_t             U4;
typedef uint64_t             U8;
typedef uint64_t             U8;
typedef int8_t               I1;
typedef int16_t              I2;
typedef int32_t              I4;
typedef int64_t              I8;

typedef struct { uint8_t* dat; uint32_t len; uint32_t cap; } CBuf;
typedef struct { uint8_t* dat; uint32_t len; uint32_t cap;
                 uint32_t plc; } CPlcBuf;

U4 minU4(U4 a, U4 b);
U4 maxU4(U4 a, U4 b);

// #################################
// # Roles

// For declaring role methods. This Expands:
//   Role_METHOD(myFunc, U1, U2)
// to
//   void (*)(void*, U1, U2) myFunc
#define Role_METHOD(M, ...)  ((void (*)(void*) __VA_OPT__(,) __VA_ARGS__) M)


#define Role_AS_DECLARE(TO, FROM) (TO)*  as ## TO ((FROM)* f)
#define Role_AS        (TO, FROM) \
  Role_AS_DECLARE(TO, FROM) { return ((TO)*) f; }

// #################################
// # File Role

// File Methods
typedef struct {
  void (*open)  (void* d);
  void (*close) (void* d);
  void (*stop)  (void* d);
  void (*seek)  (void* d);
  void (*clear) (void* d);
  void (*read)  (void* d);
  void (*insert)(void* d);
} M_File;

typedef struct {
  uint64_t pos;   // current position in file. If seek: desired position.
  uint64_t fid;   // file id or reference
  CBuf     buf;   // buffer for reading or writing data
  uint32_t plc;   // place, makes buf a PlcBuf. write: write pos.
  uint16_t code;  // status or error (File_*)
} File;

// If set it is a real "file index/id"
#define File_INDEX      (1ULL << ((sizeof(uint64_t) * 8) - 1))

const uint16_t File_SEEKING  = 0x00;
const uint16_t File_READING  = 0x01;
const uint16_t File_WRITING  = 0x02;
const uint16_t File_STOPPING = 0x03;

const uint16_t File_DONE     = 0xD0;
const uint16_t File_STOPPED  = 0xD1;
const uint16_t File_EOF      = 0xD2;

const uint16_t File_ERROR    = 0xE0;
const uint16_t File_EPERM    = 0xE1;
const uint16_t File_EIO      = 0xE2;

#endif // __CIV_H
