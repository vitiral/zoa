#include <stdlib.h>
#include <stdio.h>
#include <stddef.h>
#include <unistd.h>
#include <fcntl.h>

#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <string.h>

#include "./civ.h"

#define UFile_FD(F)      ((~File_INDEX) & (F).fid)

U4 minU4(U4 a, U4 b) { if(a < b) return a; return b; }
U4 maxU4(U4 a, U4 b) { if(a < b) return b; return a; }

int UFile_handleErr(File* f, int res) {
  if(errno == EWOULDBLOCK) return res;
  if(res < 0) { f->code = File_EIO; }
  return res;
}

void UFile_open(File* f) {
  assert(f->buf.len < 255);
  uint8_t pathname[256];
  memcpy(pathname, f->buf.dat, f->buf.len);
  pathname[f->buf.len] = 0;
  int fd = UFile_handleErr(f, open(pathname, O_NONBLOCK, O_RDWR));
  if(fd < 0) return;
  f->pos = 0; f->fid = File_INDEX | fd;
  f->buf.len = 0; f->plc = 0; f->code = File_DONE;
}

void UFile_close(File* f) {
  if(close(UFile_FD(*f))) f->code = File_ERROR;
  else                   f->code = File_DONE;
}

void UFile_read(File* f) {
  assert(f->code == File_READING || f->code >= File_DONE);
  int len;
  if(!(File_INDEX & f->fid)) { // mocked file.
    CPlcBuf* p = (CPlcBuf*) f->fid;
    len = minU4(p->len - p->plc, f->buf.cap - f->buf.len);
    memmove(f->buf.dat, p->dat + p->plc, len); p->plc += len;
  } else {
    f->code = File_READING;
    len = read(UFile_FD(*f), f->buf.dat + f->buf.len, f->buf.cap - f->buf.len);
    len = UFile_handleErr(f, len);  assert(len >= 0);
  }
  f->buf.len += len; f->pos += len;
  if(f->buf.len == f->buf.cap) f->code = File_DONE;
  else if (0 == len)           f->code = File_EOF;
}

M_File M_UFile = (M_File) {
  .open  = Role_METHOD(UFile_open),
  .close = Role_METHOD(UFile_close),
  .stop = NULL,
  .seek = NULL,
  .clear = NULL,
  .read = Role_METHOD(UFile_read),
  .insert = NULL,
};

void main() {
  uint64_t direct                     = 1ULL << 63;
  uint64_t calculated = 1; calculated = calculated << 63;
  printf("direct: %llx  calculated: %llx\n", File_INDEX, calculated);
}
