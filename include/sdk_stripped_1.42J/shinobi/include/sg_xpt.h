#ifndef SG_XPT_H
#define SG_XPT_H
#ifdef __cplusplus
#define EXTERN  extern ""
#else
#define EXTERN  extern
#endif
#ifdef  _OPT_SNB
#define _XPT_CPU_SH4
#define _XPT_LIB_SNB
#define _XPT_CC_SHC
#define _XPT_END_LTL
#endif
#ifndef _TYPEDEF_Uint8
#define _TYPEDEF_Uint8
typedef unsigned char     Uint8;
#endif
#ifndef _TYPEDEF_Sint8
#define _TYPEDEF_Sint8
typedef signed char     Sint8;
#endif
#ifndef _TYPEDEF_Uint16
#define _TYPEDEF_Uint16
typedef unsigned short  Uint16;
#endif
#ifndef _TYPEDEF_Sint16
#define _TYPEDEF_Sint16
typedef signed short    Sint16;
#endif
#ifndef _TYPEDEF_Uint32
#define _TYPEDEF_Uint32
typedef unsigned long   Uint32;
#endif
#ifndef _TYPEDEF_Sint32
#define _TYPEDEF_Sint32
typedef signed long     Sint32;
#endif
#ifndef _TYPEDEF_Float32
#define _TYPEDEF_Float32
typedef float           Float32;
#endif
#ifndef _TYPEDEF_Float64
#define _TYPEDEF_Float64
typedef double          Float64;
#endif
#ifndef _TYPEDEF_Float
#define _TYPEDEF_Float
typedef float           Float;
#endif
#ifndef _TYPEDEF_Double
#define _TYPEDEF_Double
typedef double           Double;
#endif
#ifndef _TYPEDEF_Void
#define _TYPEDEF_Void
typedef void            Void;
#endif
#ifdef __SHC__
#ifndef __cplusplus
enum bool
{
    false,
    true
};
typedef enum bool   bool;
#endif
#endif
#ifndef _TYPEDEF_Bool
#define _TYPEDEF_Bool
typedef Sint32 Bool ;
#endif
#ifndef  NULL
#ifdef  __cplusplus
#define  NULL           (0)
#else
#define  NULL           ((void *)0)
#endif
#endif
#ifndef NO
#define NO              (0)
#endif
#ifndef YES
#define YES             (1)
#endif
#ifndef FALSE
#define FALSE           (0)
#endif
#ifndef TRUE
#define TRUE            (1)
#endif
#ifndef OFF
#define OFF             (0)
#endif
#ifndef ON
#define ON              (1)
#endif
#ifndef OK
#define OK              (0)
#endif
#ifndef NG
#define NG              (-1)
#endif
#ifndef MAX
#define MAX(x, y)       ((x) > (y) ? (x) : (y))
#endif
#ifndef MIN
#define MIN(x, y)       ((x) < (y) ? (x) : (y))
#endif
#ifndef ABS
#define ABS(x)          ((x) < 0 ? -(x) : (x))
#endif
#endif
