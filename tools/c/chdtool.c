/* chdtool: open a CHD with libchdr (block CRC verification on) and dump the logical data. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libchdr/chd.h>
int main(int argc, char **argv){
  chd_file *chd; chd_error e = chd_open(argv[1], CHD_OPEN_READ, NULL, &chd);
  if (e) { printf("open error %d %s\n", e, chd_error_string(e)); return 1; }
  const chd_header *h = chd_get_header(chd);
  fprintf(stderr, "version %u hunkbytes %u hunks %u logical %llu\n", h->version, h->hunkbytes, h->totalhunks, (unsigned long long)h->logicalbytes);
  FILE *o = argc > 2 ? fopen(argv[2], "wb") : NULL;
  unsigned char *buf = malloc(h->hunkbytes); unsigned long long left = h->logicalbytes;
  for (unsigned i = 0; i < h->totalhunks; i++) {
    e = chd_read(chd, i, buf);
    if (e) { printf("hunk %u error %d %s\n", i, e, chd_error_string(e)); return 2; }
    unsigned n = left < h->hunkbytes ? (unsigned)left : h->hunkbytes;
    if (o) fwrite(buf, 1, n, o); left -= n;
  }
  char meta[512]; uint32_t len, tag; uint8_t fl;
  for (int i = 0; ; i++) {
    if (chd_get_metadata(chd, CHDMETATAG_WILDCARD, i, meta, sizeof meta, &len, &tag, &fl)) break;
    fprintf(stderr, "meta %c%c%c%c %s\n", tag>>24, tag>>16, tag>>8, tag, meta);
  }
  if (o) fclose(o);
  printf("OK\n"); chd_close(chd); return 0;
}
