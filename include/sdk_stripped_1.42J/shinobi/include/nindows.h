#ifndef _NINDOWS_H_
#define _NINDOWS_H_
#ifdef __cplusplus
extern ""{
#endif
#include <Ninja.h>
#define NWD_SM_CXSIZEFRAME  2
#define NWD_SM_CYSIZEFRAME  2
#define NWD_SM_CXBORDER     1
#define NWD_SM_CYBORDER     1
#define NWD_SM_CXMINTRACK   32
#define NWD_SM_CYMINTRACK   10
#define NWD_SM_CYCAPTION    20
#define NWD_SM_SZCAPTION    16
#define NWD_SM_CXSHADOW     8
#define NWD_SM_CYSHADOW     8
#define NWD_WS_CAPTION      0x00000001
#define NWD_WS_THICKFRAME   0x00000002
#define NWD_WS_BORDER       0x00000004
#define NWD_WS_SHADING      0x00000008
#define NWD_WS_CONTROL      0x00000010
#define NWD_WS_OFFSET       0x00000020
#define NWD_WS_SHADOW       0x00000040
#define NWD_WS_INVISIBLE    0x00000080
#define NWD_WS_NOMOVE       0x00000100
#define NWD_WS_CLOSEBOX     NWD_WS_CONTROL
#define NWD_WS_MAXIMIZEBOX  0x00000200
#define NWD_WS_MINIMIZEBOX  0x00000400
#define NWD_WS_SB_HORZ      0x00001000
#define NWD_WS_SB_VERT      0x00002000
#define NWD_WS_CLOSE        0x80000000
enum {
	NWD_WC_WIN,
	NWD_WC_BUTTON,
	NWD_WC_SCRBAR,
	NWD_WC_SCRWIN,
	NWD_WC_EDITWIN,
	NWD_WC_MENUWIN,
	NWD_WC_CTLBOX
};
#define NWD_BS_DOWN         0x00000001
#define NWD_BS_INVOKED      0x00000100
#define NWD_BS_GRAYED       0x00000002
#define NWD_MS_MOVE         0x00010000
#define NWD_MS_BUTTON       0x000f
#define NWD_MS_LBUTTON      0x0001
#define NWD_MS_RBUTTON      0x0002
#define NWD_MS_MBUTTON      0x0004
#define NWD_MS_BUTTONDOWN   0x00f0
#define NWD_MS_LBUTTONDOWN  0x0010
#define NWD_MS_RBUTTONDOWN  0x0020
#define NWD_MS_MBUTTONDOWN  0x0040
#define NWD_MS_BUTTONUP     0x0f00
#define NWD_MS_LBUTTONUP    0x0100
#define NWD_MS_RBUTTONUP    0x0200
#define NWD_MS_MBUTTONUP    0x0400
#define NWD_MS_LBUTTONUP    0x0100
#define NWD_MS_RBUTTONUP    0x0200
#define NWD_MS_MBUTTONUP    0x0400
#define NWD_MS_CONTROL      0x1000
#define NWD_MS_SHIFT        0x2000
#define NWD_MCS_DRAG        0x40000000
#define NWD_MCS_RESIZE      0x20000000
#define NWD_MCS_AREAMASK    0x0000ffff
#define NWD_MCS_AREAFRAMET      0x0001
#define NWD_MCS_AREAFRAMELT     0x0002
#define NWD_MCS_AREAFRAMEL      0x0003
#define NWD_MCS_AREAFRAMELB     0x0004
#define NWD_MCS_AREAFRAMEB      0x0005
#define NWD_MCS_AREAFRAMERB     0x0006
#define NWD_MCS_AREAFRAMER      0x0007
#define NWD_MCS_AREAFRAMERT     0x0008
#define NWD_MCS_AREACLIENT      0x0009
#define NWD_MCS_AREACAPTION     0x000a
#define NWD_ES_HORIZONTAL       0x00000001
#define NWD_ES_VERTICAL         0x00000002
#define NWD_ES_USECLIP          0x00010000
enum {
	NWD_MSG_NULL,
	NWD_MSG_ALL,
	NWD_MSG_CLICK,
	NWD_MSG_LBUTTONDOWN,
	NWD_MSG_FOCUS,
	NWD_MSG_CLOSE
};
enum {
	NWD_DT_CHAR,
	NWD_DT_SHORT,
	NWD_DT_INT,
	NWD_DT_LONG,
	NWD_DT_FLOAT,
	NWD_DT_UCHAR,
	NWD_DT_USHORT,
	NWD_DT_UINT,
	NWD_DT_ULONG
};
#define NWD_MF_NULL       0x0000
#define NWD_MF_NORMAL     0x0001
#define NWD_MF_SEPARATOR  0x0002
#define NWD_MF_POPUP      0x0004
#define NWD_MF_CHECKED    0x8000
#define NWD_MF_GRAYED     0x0008
#define NWD_FONTTYPE_SMALL  1
#define NWD_FONTTYPE_NORMAL 2
#define NWD_FONTTYPE_LARGE  3
#define NWD_DEFWIN_SYSMENU     0
#define NWD_DEFWIN_NINJAINFO   1
#define NWD_DEFWIN_WINDOWINFO  2
#define NWD_DEFWIN_TEXCONTROL  3
#define NWD_DEFWIN_TEXVIEWER   4
#define NWD_DEFWIN_PERINFO     5
#define NWD_DEFWIN_DEBUG       6
#define NWD_DEFWIN_PERFORMANCE 7
typedef struct _NWS_RGBA {
	Uint8 r;
	Uint8 g;
	Uint8 b;
	Uint8 a;
} NWS_RGBA;
typedef struct _NWS_RECT {
	Sint32 left;
	Sint32 top;
	Sint32 right;
	Sint32 bottom;
} NWS_RECT;
typedef struct _NWS_RECTF {
	Float left;
	Float top;
	Float right;
	Float bottom;
} NWS_RECTF;
typedef struct _NWS_POINT {
	Sint32 x, y;
} NWS_POINT;
typedef struct _NWS_MOUSE {
	NWS_POINT pt;
	Sint32    dt;
	Sint32    cursor;
	NWS_POINT oldPt;
	NWS_POINT mv;
	NWS_POINT dragPt;
} NWS_MOUSE;
#define nwSetRGBA(_d, _r, _g, _b, _a)	\
	((_d)->r = (_r), (_d)->g = (_g), (_d)->b = (_b), (_d)->a = (_a))
#define nwSetRect(a, b , c, d, e)	\
	((a)->left = (b), (a)->top = (c), (a)->right = (d), (a)->bottom = (e))
typedef Bool (*NWF_MSGPROC)(Sint32 msg, Sint32 param1, Sint32 param2);
typedef struct _NWS_MSGHANDLE {
	Sint32      msg;
	NWF_MSGPROC func;
} NWS_MSGHANDLE;
typedef struct _NWS_DATA {
	void *dt;
	Sint32 type;
} NWS_DATA;
typedef struct _NWS_WIN {
	Sint32 style;
	Sint32 wClass;
	char* caption;
	Sint32 font;
	struct _NWS_WIN* parent;
	struct _NWS_WIN* child;
	struct _NWS_WIN* before;
	struct _NWS_WIN* next;
	Sint32 x, y;
	Sint32 w, h;
	NWS_RGBA col[4];
	NWS_MSGHANDLE* msgHandle;
	void* menuTable;
	void* userBuf;
	void (*clientDraw)(struct _NWS_WIN *NWFUNC);
	void (*execFunc)(struct _NWS_WIN *NWFUNC);
	void (*destructor)(struct _NWS_WIN* NWFUNC);
	Sint32 param1, param2;
	struct _NWS_WIN* hClose;
	struct _NWS_WIN* hMaximize;
	struct _NWS_WIN* hMinimize;
} NWS_WIN;
typedef NWS_WIN* NWHWND;
typedef void (*NWF_BUTTONFUNC)(NWHWND);
typedef struct _NWS_BUTTON {
	NWS_WIN         base;
	NWF_BUTTONFUNC  func;
	Sint32          state;
	Sint32          count;
} NWS_BUTTON;
typedef struct _NWS_SCRBAR {
	NWS_WIN base;
	Float pos;
	Float min;
	Float max;
	Float lineMove;
	Float pageMove;
	NWS_DATA dt;
} NWS_SCRBAR;
typedef struct {
	char* caption;
	NWS_DATA data;
	Float min, max;
	Float line, page;
	Float pos;
} NWS_SCROLLBARINFO;
typedef struct {
	Sint32 n;
	Sint32 style;
	Sint16 x, y;
	Sint16 w, h;
	NWS_SCROLLBARINFO* info;
} NWS_SCROLLBARLIST;
typedef struct _NWS_SCRWIN {
	NWS_WIN base;
	Sint32 sx, sy;
	Sint32 flag;
	NWS_RECT clip;
} NWS_SCRWIN;
typedef struct _NWS_EDITLINE {
	struct _NWS_EDITLINE* before;
	struct _NWS_EDITLINE* next;
	Sint8* buf;
	Sint32 len;
} NWS_EDITLINE;
typedef struct _NWS_EDITWIN {
	NWS_SCRWIN base;
	Sint32 maxLine;
	NWS_EDITLINE* lineBuf;
	Sint32 lineSum;
	NWS_EDITLINE* startLine;
	NWS_EDITLINE* curLine;
} NWS_EDITWIN;
typedef void (*NWF_MENUHANDLE)(NWHWND, Sint32 idx, Sint32 param);
typedef struct _NWS_MENUTABLE {
	Sint32         type;
	char*          title;
	NWF_MENUHANDLE func;
	Sint32         param;
} NWS_MENUTABLE;
typedef struct _NWS_MENUWIN {
	NWS_WIN       base;
	Sint32        check;
	NWS_MENUTABLE* menuTable;
} NWS_MENUWIN;
typedef struct _NWS_FONT {
	Sint32      baseChar;
	Sint32      w,  h;
	Sint32      u, v;
	Sint32      gw, gh;
	Sint32      dw;
	NJS_TEXNAME* texname;
	Uint32      globalIndex;
} NWS_FONT;
#if 1
void nwInitSystem(Uint32 numTextures, Uint32 port);
#else
void nwInitSystem(Uint32 numTextures);
#endif
Sint32 nwExecute(void);
void nwExitSystem(void);
void nwInitResource(void);
Uint32 nwVersion(void);
Float nwGetZ(void);
Float nwAddZ(void);
NWHWND nwCreateMenuWindow(NWS_MENUTABLE* menuTbl, const char* caption,
            Sint32 x, Sint32 y, NWHWND parent);
void nwTextOut(NWHWND hWnd, Sint32 x, Sint32 y, const char* fmt, ...);
void nwSetTextColor(NWS_RGBA* col);
Sint32 nwGetFontSize(Sint32* width, Sint32* height);
void nwSelectSystemFont(Sint32 fonttype);
NWHWND nwCreateButton(NWF_BUTTONFUNC func, const char* title,
	Sint32 x, Sint32 y, Sint32 w, Sint32 h, NWHWND parent);
void nwEnableButton(NWHWND hWnd, Bool flag);
NWHWND nwCreateScrollBar(Sint32 type, const char* title,
	Sint32 x, Sint32 y, Sint32 w, Sint32 h, NWHWND parent);
void nwSetScrollBarPos(NWHWND hWnd, Float pos);
void nwSetScrollBarRange(NWHWND hWnd, Float min, Float max);
void nwSetScrollBarData(NWHWND hWnd, NWS_DATA *dt);
void nwSetScrollBarLineMove(NWHWND hWnd, Float step);
void nwSetScrollBarPageMove(NWHWND hWnd, Float step);
void nwCreateScrollBarArray(NWS_SCROLLBARLIST* list, NWHWND parent);
Bool nwScrWinEnableScroll(NWHWND hWnd, Sint32 flag);
Bool nwScrWinSetClip(NWHWND hWNd, NWS_RECT* rect);
Bool nwScrWinScroll(NWHWND hWnd, Sint32 x, Sint32 y);
Bool nwScrWinGetScroll(NWHWND hWnd, Sint32* x, Sint32* y);
NWHWND nwCreateEditWindow(Sint32 lineSum, const char* caption, Sint32 style,
	Sint32 x, Sint32 y, Sint32 w, Sint32 h, NWHWND parent);
Bool nwEditWinAddString(NWHWND hWnd, const char* string);
Bool nwEditWinPrintf(NWHWND hWnd, const char* fmt, ...);
NWHWND nwCreateWindow(Sint32 wClass, const char* caption, Sint32 style,
	Sint32 x, Sint32 y, Sint32 w, Sint32 h, NWHWND parent);
void nwDestroyWindow(NWHWND hWnd);
void nwBringWindowToTop(NWHWND hWnd);
NWHWND nwFindWindow(NWHWND hWnd, const char* name);
NWHWND nwFindWindowByPos(Sint16 x, Sint16 y);
NWHWND nwFindWindowEx(NWHWND hWnd, const char* name);
void nwGetClientRect(NWHWND hWnd, NWS_RECT* rc);
Bool nwGetWindowColor(NWHWND hWnd, NWS_RGBA* col);
Bool nwGetWindowPos(NWHWND hWnd, Sint32* x, Sint32* y);
void nwGetWindowRect(NWHWND hWnd, NWS_RECT* rc);
Bool nwGetWindowSize(NWHWND hWnd, Sint32* w, Sint32* h);
Bool nwGetWindowStyle(NWHWND hWnd, Sint32* style);
Sint32 nwGetWindowText(NWHWND hWnd, char *buf, Sint32 size);
Bool nwSetWindowColor(NWHWND hWnd, NWS_RGBA* col);
Bool nwSetWindowStyle(NWHWND hWnd, Sint32 and_style, Sint32 or_style);
Bool nwSetWindowPos(NWHWND hWnd, Sint32 x, Sint32 y);
Bool nwSetWindowSize(NWHWND hWnd, Sint32 w, Sint32 h);
Bool nwSetWindowText(NWHWND hWnd, const char* text);
NWHWND nwCreateColorDialog(Sint32 x, Sint32 y, NWS_RGBA* rgba, NWHWND parent);
NWHWND nwCreatePropertyDialog(NWHWND hWnd, Sint32 x, Sint32 y);
void nwDebugPrintf(Sint8 *fmt, ...);
void nwSetDefWindowColor(Sint32 win, NWS_RGBA* col);
void nwSetDefWindowStyle(Sint32 win, Sint32 and_style, Sint32 or_style);
void nwSetDefWindowPos(Sint32 win, Sint32 x, Sint32 y);
void nwSetDefWindowSize(Sint32 win, Sint32 w, Sint32 h);
void nwSetUserMenu(NWS_MENUTABLE* menu);
void nwGetMousePosition(Sint32* x, Sint32* y);
void nwSetMousePosition(Sint32 x, Sint32 y);
void nwGetMouseSpeed(Sint32* x, Sint32* y);
void nwSetMouseSpeed(Sint32 x, Sint32 y);
void nwEnablePeripheral(Bool flag);
#ifdef __cplusplus
}
#endif
#endif
