/* Test-only actual native allocation accounting/fault injection. */
#include "tokenizer_lifetime.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
void *__real_realloc(void *,size_t);
void __real_free(void *);
static struct { void *pointer; size_t size; } slots[8192];
static size_t live, bytes, peak, calls, fail_at;
static int tracking, rejected;
static int deny(void) {
    if (!tracking) return 0;
    calls++;
    if (fail_at && calls == fail_at) { rejected=1; return 1; }
    return 0;
}
static void remove_pointer(void *p) {
    if (!p) return;
    for (size_t i=0;i<8192;i++) if (slots[i].pointer==p) {
        live--; bytes-=slots[i].size; slots[i].pointer=NULL; return;
    }
}
static void add_pointer(void *p,size_t n) {
    if (!tracking || !p) return;
    for (size_t i=0;i<8192;i++) if (!slots[i].pointer) {
        slots[i].pointer=p; slots[i].size=n; live++; bytes+=n;
        if (bytes>peak) peak=bytes;
        if (bytes>16777216) { fprintf(stderr,"tokenizer retained over 16MiB\n"); abort(); }
        return;
    }
    fprintf(stderr,"tokenizer allocation slots exhausted\n"); abort();
}
void *__wrap_malloc(size_t n) { if(deny())return NULL;void*p=__real_malloc(n);add_pointer(p,n);return p; }
void *__wrap_calloc(size_t n,size_t s) { if(deny())return NULL;void*p=__real_calloc(n,s);add_pointer(p,n*s);return p; }
void *__wrap_realloc(void *p,size_t n) {
    if(deny())return NULL;
    void *result=__real_realloc(p,n);
    if(result||!n){remove_pointer(p);add_pointer(result,n);}
    return result;
}
void __wrap_free(void *p) {remove_pointer(p);__real_free(p);}
static int balanced(const char *phase,size_t at) {
    if (!live && !bytes) return 1;
    fprintf(stderr,"%s at %zu retained allocations=%zu bytes=%zu\n",phase,at,live,bytes);return 0;
}
int main(void) {
    if(Prepare()!=42)return 1;
    tracking=1;
    for(size_t i=0;i<2000;i++)if(Exercise()!=42||!balanced("encode",i))return 2;
    calls=0;
    if(Exercise()!=42||!balanced("encode baseline",0))return 3;
    size_t encode_calls=calls;
    for(size_t i=1;i<=encode_calls;i++) {
        calls=0;fail_at=i;rejected=0;
        int result=Exercise();
        if(!rejected||result!=0||!balanced("encode fault",i))return 4;
    }
    fail_at=0;calls=0;
    if(Exercise()!=42||!balanced("encode recovery",0))return 8;
    calls=0;
    if(LoadOnce()!=42||!balanced("load baseline",0))return 5;
    size_t load_calls=calls;
    for(size_t i=1;i<=load_calls;i++) {
        calls=0;fail_at=i;rejected=0;
        int result=LoadOnce();
        if(!rejected||result!=0||!balanced("load fault",i)) {
            fprintf(stderr,"load fault %zu result=%d rejected=%d\n",i,result,rejected);return 6;
        }
    }
    fail_at=0;
    for(size_t i=0;i<50;i++)if(LoadOnce()!=42||!balanced("reload",i))return 7;
    tracking=0;Finish();
    fprintf(stderr,"CLIP native lifetime: 2000 encodes, 50 reloads, %zu encode/%zu load faults; live=%zu bytes=%zu peak=%zu\n",encode_calls,load_calls,live,bytes,peak);
    return 0;
}
