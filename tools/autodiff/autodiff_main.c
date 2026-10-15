/* Driver for tools/dc/autodiff.py. Reads the case file, runs ad_wrapper() per case, prints the result in the
 * same shape as the emulator: "ret=<hex> C<callee>=a,b,... rbytes:<addr>:<len>=<hex> ...". */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "autodiff.h"

#define MAXREG 32
#define MAXCALLEE 64
static struct { uint32_t addr, len; uint8_t *buf; } reg[MAXREG]; static int nreg;
static struct { uint32_t addr; uint32_t rets[64]; int nret, hits; } cal[MAXCALLEE]; static int ncal;
static char *log_; static size_t loglen, logcap;

static void logf_(const char *fmt, ...);
#include <stdarg.h>
static void logf_(const char *fmt, ...)
{
    char tmp[256]; va_list ap; int n;
    va_start(ap, fmt); n = vsnprintf(tmp, sizeof tmp, fmt, ap); va_end(ap);
    if (loglen + (size_t)n + 1 > logcap) { logcap = (loglen + n + 1) * 2; log_ = realloc(log_, logcap); }
    memcpy(log_ + loglen, tmp, n + 1); loglen += n;
}

uint8_t *ad_mem(uint32_t addr)
{
    int i;
    for (i = 0; i < nreg; i++)
        if (addr >= reg[i].addr && addr < reg[i].addr + reg[i].len) return reg[i].buf + (addr - reg[i].addr);
    fprintf(stderr, "ad_mem: address %08x is outside every declared region (declare it in the spec)\n", addr);
    abort();
}
uint32_t ad_rd32(uint32_t a) { uint8_t *p = ad_mem(a); return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24); }

uint32_t ad_call(uint32_t callee, const uint32_t *ints, int ni, const uint32_t *fl, int nf)
{
    int i, k;
    logf_(" C%x=", callee);
    for (i = 0; i < ni; i++) logf_("%x,", ints[i]);
    for (i = 0; i < nf; i++) logf_("%x,", fl[i]);
    for (k = 0; k < ncal; k++)
        if (cal[k].addr == callee) {
            uint32_t v = cal[k].nret ? cal[k].rets[cal[k].hits < cal[k].nret ? cal[k].hits : cal[k].nret - 1] : 0;
            cal[k].hits++; return v;
        }
    fprintf(stderr, "ad_call: callee %x is not declared in the spec (\"callees\")\n", callee); abort();
}

static int hexv(int c) { return c <= '9' ? c - '0' : (c | 32) - 'a' + 10; }

int main(void)
{
    static char line[1 << 22];
    while (fgets(line, sizeof line, stdin)) {
        char *tok, *save; ad_regs c; int k;
        if (!strncmp(line, "region ", 7)) {          /* region <addr> <len> */
            unsigned a, l; sscanf(line + 7, "%x %u", &a, &l);
            reg[nreg].addr = a; reg[nreg].len = l; reg[nreg].buf = calloc(l, 1); nreg++; continue;
        }
        if (!strncmp(line, "callee ", 7)) {          /* callee <addr> [v0,v1,..] */
            unsigned a; char rs[1024] = ""; char *p;
            sscanf(line + 7, "%x %1023s", &a, rs);
            cal[ncal].addr = a; cal[ncal].nret = 0;
            for (p = strtok(rs, ","); p; p = strtok(NULL, ",")) cal[ncal].rets[cal[ncal].nret++] = (uint32_t)strtoul(p, NULL, 16);
            ncal++; continue;
        }
        /* case: "r4=.. fr4=.. m<addr>=<hex bytes> ..." */
        memset(&c, 0, sizeof c); loglen = 0; if (log_) log_[0] = 0;
        for (k = 0; k < ncal; k++) cal[k].hits = 0;
        for (tok = strtok_r(line, " \n", &save); tok; tok = strtok_r(NULL, " \n", &save)) {
            char *eq = strchr(tok, '='); if (!eq) continue; *eq++ = 0;
            if (tok[0] == 'r' && tok[1] != 0) c.r[atoi(tok + 1)] = (uint32_t)strtoul(eq, NULL, 16);
            else if (tok[0] == 'f' && tok[1] == 'r') c.fr[atoi(tok + 2)] = (uint32_t)strtoul(eq, NULL, 16);
            else if (tok[0] == 'm') {
                uint8_t *d = ad_mem((uint32_t)strtoul(tok + 1, NULL, 16)); size_t n = strlen(eq) / 2, i;
                for (i = 0; i < n; i++) d[i] = (hexv(eq[2 * i]) << 4) | hexv(eq[2 * i + 1]);
            }
        }
        ad_wrapper(&c);
        printf("ret=%x%s", c.ret, log_ ? log_ : "");
        for (k = 0; k < nreg; k++) {
            uint32_t i; printf(" rbytes:%x:%u=", reg[k].addr, reg[k].len);
            for (i = 0; i < reg[k].len; i++) printf("%02x", reg[k].buf[i]);
        }
        printf("\n"); fflush(stdout);
    }
    return 0;
}
