#ifndef _NINJA_STR_H_
#define _NINJA_STR_H_
typedef Sint8 NJS_SYS_ATTR[NJD_SYS_ATTR_SIZE];
typedef void (*NJS_INT_FUNC)(void);
typedef struct{
	Uint32 NativeLimit;
	Uint32 NativeCurrent;
	Uint32 NativePeak;
	Uint32 InternalVertexBufSize[5];
	Uint32 MaxVertexBufSize[5];
	Uint32 LastTATime;
	Uint32 LastRenderTime;
	Uint32 CurrentVertexBufSize[5];
	Uint32 reserved0;
	Uint32 reserved1;
	Uint32 reserved2;
	Uint32 reserved3;
	Uint32 reserved4;
	Uint32 reserved5;
	Uint32 reserved6;
	Uint32 reserved7;
	Uint32 reserved8;
	Uint32 reserved9;
	Uint32 reserved10;
	Uint32 reserved11;
} NJS_SYSTEMINFO;
typedef struct {
	Sint16  u;
	Sint16  v;
} NJS_TEX;
typedef	struct {
	Uint8   b;
	Uint8   g;
	Uint8   r;
	Uint8   a;
} NJS_BGRA;
typedef union {
	Uint32  color;
	NJS_TEX tex;
	NJS_BGRA argb;
} NJS_COLOR;
typedef struct {
	Float   a;
	Float   r;
	Float   g;
	Float   b;
} NJS_ARGB;
typedef struct {
	Sint16  x;
	Sint16  y;
} NJS_POINT2I;
typedef struct {
	Float  x;
	Float  y;
} NJS_POINT2;
typedef struct {
	Float   x;
	Float   y;
	Float   z;
} NJS_POINT3, NJS_VECTOR;
typedef struct {
	NJS_POINT2  *p;
	NJS_COLOR   *col;
    NJS_COLOR   *tex;
    Uint32      num;
} NJS_POINT2COL;
typedef struct {
	NJS_POINT3  *p;
	NJS_COLOR   *col;
    NJS_COLOR   *tex;
    Uint32      num;
} NJS_POINT3COL;
typedef struct {
	Float   px,py,pz;
	Float   vx,vy,vz;
} NJS_LINE, NJS_PLANE, NJS_PVECTOR;
typedef struct{
    NJS_POINT3 c;
    Float      r;
} NJS_SPHERE;
typedef struct{
    NJS_POINT3 c1;
    NJS_POINT3 c2;
    Float      r;
} NJS_CAPSULE;
typedef struct{
    NJS_POINT3 v[8];
} NJS_BOX;
typedef struct{
    NJS_POINT3 v[4];
} NJS_RECT;
typedef struct {
	NJS_MATRIX m;
	Float   px,py,pz;
	Float   vx,vy,vz;
	Angle   roll;
	Float   apx,apy,apz;
	Float   avx,avy,avz;
	Angle   aroll;
} NJS_VIEW;
typedef struct {
	Float   dist;
	Float   w,h;
	Float   cx,cy;
} NJS_SCREEN;
typedef struct{
	Uint32 Type;
	Uint32 BitDepth;
	Uint32 PixelFormat;
	Uint32 nWidth;
	Uint32 nHeight;
	Uint32 TextureSize;
	Uint32 fSurfaceFlags;
	Uint32 *pSurface;
	Uint32 *pVirtual;
	Uint32 *pPhysical;
}NJS_TEXSURFACE;
typedef struct{
	void*			   texaddr;
	NJS_TEXSURFACE	texsurface;
} NJS_TEXINFO;
typedef struct {
	void            *filename;
	Uint32               attr;
	Uint32            texaddr;
} NJS_TEXNAME;
typedef struct {
	NJS_TEXNAME     *textures;
	Uint32          nbTexture;
} NJS_TEXLIST;
typedef struct {
	Uint32			globalIndex;
	Uint32			bank;
	Uint32			tspparambuffer;
	Uint32			texparambuffer;
	Uint32			texaddr;
	NJS_TEXINFO		texinfo;
	Uint16			count;
	Uint16			dummy;
} NJS_TEXMEMLIST;
typedef struct {
	void 			*palette;
	Uint16 			mode;
	Sint16 			bank;
	Sint16 			offset;
	Sint16 			count;
}NJS_TEXPALETTE;
typedef struct {
	Uint32	n;
	Uint32	globalIndex;
	Sint32	texerr;
	Sint32	gdstat;
	Sint32	gderr;
	Sint32	reserved0;
	Sint32	reserved1;
	Sint32	reserved2;
}NJS_TEXERRSTAT;
typedef struct{
	Uint32 nTextureType;
	Uint16 nWidth;
	Uint16 nHeight;
}NJS_PVRHEADERDATA;
typedef struct {
	NJS_COLOR         diffuse;
	NJS_COLOR        specular;
	Float            exponent;
	Uint32         attr_texId;
    Uint32          attrflags;
} NJS_MATERIAL;
typedef struct {
	Uint16          type_matId;
	Uint16          nbMesh;
	Sint16          *meshes;
	Uint32          *attrs;
    NJS_VECTOR      *normals;
	NJS_COLOR       *vertcolor;
	NJS_COLOR       *vertuv;
} NJS_MESHSET;
typedef struct {
	NJS_POINT3      *points;
	NJS_VECTOR      *normals;
	Sint32          nbPoint;
	NJS_MESHSET     *meshsets;
	NJS_MATERIAL    *mats;
	Uint16          nbMeshset;
    Uint16          nbMat;
	NJS_POINT3      center;
	Float			r;
} NJS_MODEL;
typedef struct obj {
    Uint32          evalflags;
	NJS_MODEL       *model;
	Float           pos[3];
	Angle           ang[3];
	Float           scl[3];
	struct obj      *child;
	struct obj      *sibling;
} NJS_OBJECT;
typedef struct {
	Uint32          keyframe;
	Float           key[3];
} NJS_MKEY_F;
typedef struct {
	Uint32          keyframe;
	Angle           key[3];
} NJS_MKEY_A;
typedef struct {
	Uint32          keyframe;
	Angle           angle;
	Float           axe[3];
} NJS_MKEY_AX;
typedef struct
{
	Uint32          keyframe;
	void            *key;
} NJS_MKEY_P;
typedef struct {
	Uint32          keyframe;
	Float           key;
} NJS_MKEY_F1;
typedef struct {
	Uint32          keyframe;
	Float           key[2];
} NJS_MKEY_F2;
typedef struct {
	Uint32          keyframe;
	Float           nrang;
	Float           frang;
	Angle           iang;
	Angle           oang;
} NJS_MKEY_SPOT;
typedef struct {
	Uint32          keyframe;
	Uint32          key;
} NJS_MKEY_UI32;
typedef struct {
	Uint32          keyframe;
	Sint32          key;
} NJS_MKEY_SI32, NJS_MKEY_A1;
typedef struct {
    Uint32          keyframe;
    Float           key[4];
} NJS_MKEY_QUAT;
typedef struct {
	void            *p[1];
	Uint32          nb[1];
} NJS_MDATA1;
typedef struct {
	void            *p[2];
	Uint32          nb[2];
} NJS_MDATA2;
typedef struct {
	void            *p[3];
	Uint32          nb[3];
} NJS_MDATA3;
typedef struct {
	void            *p[4];
	Uint32          nb[4];
} NJS_MDATA4;
typedef struct {
	void            *p[5];
	Uint32          nb[5];
} NJS_MDATA5;
typedef struct {
	void            *mdata;
	Uint32          nbFrame;
	Uint16          type;
	Uint16          inp_fn;
} NJS_MOTION;
typedef struct {
	NJS_OBJECT      *object;
	NJS_MOTION      *motion;
#if 0
	NJS_TEXLIST     *texlist;
#endif
} NJS_ACTION;
typedef struct
{
	NJS_MOTION		*motion[2];
	Float			frame[2];
} NJS_MOTION_LINK;
typedef struct
{
	NJS_OBJECT		*object;
	NJS_MOTION_LINK	*motionlink;
} NJS_ACTION_LINK;
typedef union {
	Uint32		work;
	Uint32		clip;
} NJS_CLIP_BUF;
typedef struct {
	NJS_CLIP_BUF a;
	Float		sx,sy;
	Float		oow;
	NJS_POINT3	point;
	Uint32		reserve;
	Float		u,v;
	Float		inten[2];
	NJS_VECTOR	vector;
	Uint32		flag;
} NJS_VERTEX_BUF;
typedef struct {
	NJS_CLIP_BUF a;
	Float		sx,sy;
	Float		oow;
	NJS_POINT3	point;
	Uint32		reserve;
	NJS_ARGB	col;
	NJS_VECTOR	vector;
	Uint32		flag;
} NJS_VERTEX_BUF2;
typedef struct {
	NJS_CLIP_BUF a;
	Float		sx,sy;
	Float		oow;
	NJS_POINT3	point;
	Uint32		reserve;
	Float		u,v;
	Float		inten[2];
	NJS_VECTOR	vector;
	Uint32		flag;
} NJS_VERTEX_BUF_0;
typedef struct {
	NJS_CLIP_BUF a;
	Float		sx,sy;
	Float		oow;
	NJS_POINT3	point;
	Uint32		reserve;
	NJS_ARGB	col;
	NJS_VECTOR	vector;
	Uint32		flag;
} NJS_VERTEX_BUF_1;
typedef struct {
	NJS_CLIP_BUF a;
	Float		sx,sy;
	Float		oow;
	Float		u,v;
	Uint32		col[2];
	NJS_POINT3	point;
	NJS_VECTOR	vector;
	Uint32		flag;
	Uint32		reserve;
} NJS_VERTEX_BUF_3;
typedef struct {
	NJS_CLIP_BUF a;
	Float		sx,sy;
	Float		oow;
	NJS_POINT3	point;
	Uint32		reserve;
	Float		u,v;
	Float		inten[2];
	NJS_VECTOR	vector;
	Uint32		flag;
} NJS_VERTEX_BUF_7;
typedef struct {
	NJS_VECTOR	vector;
	Uint32		clip;
	Float		sx,sy;
	Float		oow;
	Float		inten;
} NJS_VERTEX_BUF_X;
typedef struct
{
	Float       ratten;
	Float       ipd;
	Float       nrr;
	Float       frr;
	Float       cosi;
	Float       cose;
	Float		idev;
	Float		odev;
	Float       rate;
	Float       intns;
	Int         exp;
	Int         reserve;
	NJS_POINT3  lpnt;
	NJS_VECTOR  lvctr;
	NJS_VECTOR  lmvctr;
	NJS_ARGB    atten;
	NJS_ARGB    amb;
	NJS_ARGB    dif;
	NJS_ARGB    spc;
	NJS_ARGB    mamb;
	NJS_ARGB    mdif;
	NJS_ARGB    mspc;
} NJS_LIGHT_CAL, *NJS_LIGHT_CAL_PTR;
typedef struct {
	Int             lsrc;
	Float           iamb;
	Float           idif;
	Float           ispc;
	Float           nrang;
	Float           frang;
	void*           func;
	Angle           iang;
	Angle           oang;
	NJS_ARGB        argb;
} NJS_LIGHT_ATTR, *NJS_LIGHT_ATTR_PTR;
typedef struct {
	NJS_MATRIX      mtrx;
	NJS_POINT3      pnt;
	NJS_VECTOR      vctr;
	Int             stat;
	Int             reserve;
	NJS_LIGHT_CAL   ltcal;
	NJS_LIGHT_ATTR  attr;
} NJS_LIGHT, *NJS_LIGHT_PTR;
typedef  struct {
	NJS_ARGB        ambient;
	NJS_ARGB        diffuse;
	NJS_ARGB        specular;
	Float           exponent;
} NJS_LIGHT_MATERIAL;
typedef void (*NJF_LIGHT_FUNC)(NJS_ARGB*, NJS_POINT3*, NJS_VECTOR*, NJS_LIGHT_PTR);
typedef struct {
	Float px, py, pz;
	Float vx, vy, vz;
	Angle roll;
	Angle ang;
	Float n_clip;
	Float f_clip;
	NJS_VECTOR lx,ly;
} NJS_CAMERA;
typedef struct {
	NJS_LIGHT	*light;
	NJS_MOTION	*motion;
} NJS_LACTION;
typedef struct {
	NJS_CAMERA	*camera;
	NJS_MOTION	*motion;
} NJS_CACTION;
typedef struct {
	Float	*pos;
	Angle	*ang;
	Float	*scl;
} NJS_MOTION_DATA;
typedef Uint32 NJS_SCLATTR;
typedef Float NJS_SCLMTRX[4];
typedef struct {
	Uint16      celps;
	Uint16      mapw;
	Uint16      maph;
	Uint16      sw,sh;
	NJS_TEXLIST* list;
	Uint32      *map;
	Float       px,py;
	Float       bx,by;
	Float       pr;
	Uint16      sflag;
	Float       sx,sy;
	Float		spx,spy;
	Uint16      mflag;
	Float       cx,cy;
	NJS_SCLMTRX m;
	Uint32      colmode;
	NJS_POINT2	clip[2];
	NJS_SCLATTR attr;
	NJS_COLOR	sclc;
}NJS_SCROLL;
enum{
	_SM00,_SM01,
	_SM10,_SM11
};
typedef struct {
	Sint16		sx,sy;
	Sint16      cx,cy;
	Sint16      u1,v1;
	Sint16      u2,v2;
	Sint16      texid;
	Sint16      attr;
} NJS_TEXANIM;
typedef struct {
	NJS_POINT3  p;
	Float       sx,sy;
	Angle       ang;
	NJS_TEXLIST *tlist;
	NJS_TEXANIM *tanim;
} NJS_SPRITE;
typedef struct {
	Float	x;
	Float	y;
	Float	z;
	Uint32	col;
} NJS_POLYGON_VTX;
typedef struct {
	Float	x;
	Float	y;
	Float	z;
	Float	u;
	Float	v;
	Uint32	col;
} NJS_TEXTURE_VTX;
typedef struct {
	Float	x;
	Float	y;
	Float	z;
	Float	u;
	Float	v;
	Uint32	bcol;
	Uint32	ocol;
} NJS_TEXTUREH_VTX;
typedef struct {
	int		keys;
	int		*iparam;
	float	*fparam;
} NJS_SPLINE;
typedef	struct {
	float	re;
	float	im[3];
} NJS_QUATERNION;
#endif
