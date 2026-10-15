#ifndef _NINJA_CNK_H_
#define _NINJA_CNK_H_
#define NJD_NULLOFF             0
#define NJD_BITSOFF             1
#define NJD_TINYOFF             8
#define NJD_MATOFF             16
#define NJD_VERTOFF            32
#define NJD_VOLOFF             56
#define NJD_STRIPOFF           64
#define NJD_ENDOFF            255
#define NJD_CN     (NJD_NULLOFF+0)
#define NJD_CE      (NJD_ENDOFF+0)
#define NJD_CB_BA   (NJD_BITSOFF+0)
#define NJD_CB_DA   (NJD_BITSOFF+1)
#define NJD_CB_EXP  (NJD_BITSOFF+2)
#define NJD_CB_CP   (NJD_BITSOFF+3)
#define NJD_CB_DP   (NJD_BITSOFF+4)
#define NJD_CT_TID  (NJD_TINYOFF+0)
#define NJD_CT_TID2 (NJD_TINYOFF+1)
#define NJD_CM_D    (NJD_MATOFF+1)
#define NJD_CM_A    (NJD_MATOFF+2)
#define NJD_CM_DA   (NJD_MATOFF+3)
#define NJD_CM_S    (NJD_MATOFF+4)
#define NJD_CM_DS   (NJD_MATOFF+5)
#define NJD_CM_AS   (NJD_MATOFF+6)
#define NJD_CM_DAS  (NJD_MATOFF+7)
#define NJD_CM_BU   (NJD_MATOFF+8)
#define NJD_CM_D2   (NJD_MATOFF+9)
#define NJD_CM_A2   (NJD_MATOFF+10)
#define NJD_CM_DA2  (NJD_MATOFF+11)
#define NJD_CM_S2   (NJD_MATOFF+12)
#define NJD_CM_DS2  (NJD_MATOFF+13)
#define NJD_CM_AS2  (NJD_MATOFF+14)
#define NJD_CM_DAS2 (NJD_MATOFF+15)
#define NJD_CV_SH     (NJD_VERTOFF+0)
#define NJD_CV_VN_SH  (NJD_VERTOFF+1)
#define NJD_CV        (NJD_VERTOFF+2)
#define NJD_CV_D8     (NJD_VERTOFF+3)
#define NJD_CV_UF     (NJD_VERTOFF+4)
#define NJD_CV_NF     (NJD_VERTOFF+5)
#define NJD_CV_S5     (NJD_VERTOFF+6)
#define NJD_CV_S4     (NJD_VERTOFF+7)
#define NJD_CV_IN     (NJD_VERTOFF+8)
#define NJD_CV_VN     (NJD_VERTOFF+9)
#define NJD_CV_VN_D8  (NJD_VERTOFF+10)
#define NJD_CV_VN_UF  (NJD_VERTOFF+11)
#define NJD_CV_VN_NF  (NJD_VERTOFF+12)
#define NJD_CV_VN_S5  (NJD_VERTOFF+13)
#define NJD_CV_VN_S4  (NJD_VERTOFF+14)
#define NJD_CV_VN_IN  (NJD_VERTOFF+15)
#define NJD_CV_VNX    (NJD_VERTOFF+16)
#define NJD_CV_VNX_D8 (NJD_VERTOFF+17)
#define NJD_CV_VNX_UF (NJD_VERTOFF+18)
#define NJD_CO_P3       (NJD_VOLOFF+0)
#define NJD_CO_P4       (NJD_VOLOFF+1)
#define NJD_CO_ST       (NJD_VOLOFF+2)
#define NJD_CS          (NJD_STRIPOFF+0)
#define NJD_CS_UVN      (NJD_STRIPOFF+1)
#define NJD_CS_UVH      (NJD_STRIPOFF+2)
#define NJD_CS_VN       (NJD_STRIPOFF+3)
#define NJD_CS_UVN_VN   (NJD_STRIPOFF+4)
#define NJD_CS_UVH_VN   (NJD_STRIPOFF+5)
#define NJD_CS_D8       (NJD_STRIPOFF+6)
#define NJD_CS_UVN_D8   (NJD_STRIPOFF+7)
#define NJD_CS_UVH_D8   (NJD_STRIPOFF+8)
#define NJD_CS_2        (NJD_STRIPOFF+9)
#define NJD_CS_UVN2     (NJD_STRIPOFF+10)
#define NJD_CS_UVH2     (NJD_STRIPOFF+11)
#define NJD_FBS_SHIFT     11
#define NJD_FBS_ZER      (0<<NJD_FBS_SHIFT)
#define NJD_FBS_ONE      (1<<NJD_FBS_SHIFT)
#define NJD_FBS_OC       (2<<NJD_FBS_SHIFT)
#define NJD_FBS_IOC      (3<<NJD_FBS_SHIFT)
#define NJD_FBS_SA       (4<<NJD_FBS_SHIFT)
#define NJD_FBS_ISA      (5<<NJD_FBS_SHIFT)
#define NJD_FBS_DA       (6<<NJD_FBS_SHIFT)
#define NJD_FBS_IDA      (7<<NJD_FBS_SHIFT)
#define NJD_FBS_MASK     (0x7<<NJD_FBS_SHIFT)
#define NJD_FBD_SHIFT     8
#define NJD_FBD_ZER      (0<<NJD_FBD_SHIFT)
#define NJD_FBD_ONE      (1<<NJD_FBD_SHIFT)
#define NJD_FBD_OC       (2<<NJD_FBD_SHIFT)
#define NJD_FBD_IOC      (3<<NJD_FBD_SHIFT)
#define NJD_FBD_SA       (4<<NJD_FBD_SHIFT)
#define NJD_FBD_ISA      (5<<NJD_FBD_SHIFT)
#define NJD_FBD_DA       (6<<NJD_FBD_SHIFT)
#define NJD_FBD_IDA      (7<<NJD_FBD_SHIFT)
#define NJD_FBD_MASK     (0x7<<NJD_FBD_SHIFT)
#define NJD_FDA_SHIFT     8
#define NJD_FDA_025      (1<<NJD_FDA_SHIFT)
#define NJD_FDA_050      (2<<NJD_FDA_SHIFT)
#define NJD_FDA_075      (3<<NJD_FDA_SHIFT)
#define NJD_FDA_100      (4<<NJD_FDA_SHIFT)
#define NJD_FDA_125      (5<<NJD_FDA_SHIFT)
#define NJD_FDA_150      (6<<NJD_FDA_SHIFT)
#define NJD_FDA_175      (7<<NJD_FDA_SHIFT)
#define NJD_FDA_200      (8<<NJD_FDA_SHIFT)
#define NJD_FDA_225      (9<<NJD_FDA_SHIFT)
#define NJD_FDA_250      (10<<NJD_FDA_SHIFT)
#define NJD_FDA_275      (11<<NJD_FDA_SHIFT)
#define NJD_FDA_300      (12<<NJD_FDA_SHIFT)
#define NJD_FDA_325      (13<<NJD_FDA_SHIFT)
#define NJD_FDA_350      (14<<NJD_FDA_SHIFT)
#define NJD_FDA_375      (15<<NJD_FDA_SHIFT)
#define NJD_FDA_MASK     (0xf<<NJD_FDA_SHIFT)
#define NJD_FEXP_SHIFT    8
#define NJD_FEXP_00      (0<<NJD_FEXP_SHIFT)
#define NJD_FEXP_01      (1<<NJD_FEXP_SHIFT)
#define NJD_FEXP_02      (2<<NJD_FEXP_SHIFT)
#define NJD_FEXP_03      (3<<NJD_FEXP_SHIFT)
#define NJD_FEXP_04      (4<<NJD_FEXP_SHIFT)
#define NJD_FEXP_05      (5<<NJD_FEXP_SHIFT)
#define NJD_FEXP_06      (6<<NJD_FEXP_SHIFT)
#define NJD_FEXP_07      (7<<NJD_FEXP_SHIFT)
#define NJD_FEXP_08      (8<<NJD_FEXP_SHIFT)
#define NJD_FEXP_09      (9<<NJD_FEXP_SHIFT)
#define NJD_FEXP_10      (10<<NJD_FEXP_SHIFT)
#define NJD_FEXP_11      (11<<NJD_FEXP_SHIFT)
#define NJD_FEXP_12      (12<<NJD_FEXP_SHIFT)
#define NJD_FEXP_13      (13<<NJD_FEXP_SHIFT)
#define NJD_FEXP_14      (14<<NJD_FEXP_SHIFT)
#define NJD_FEXP_15      (15<<NJD_FEXP_SHIFT)
#define NJD_FEXP_16      (16<<NJD_FEXP_SHIFT)
#define NJD_FEXP_MASK    (0x1f<<NJD_FEXP_SHIFT)
#define	NJD_CNK_EASY_MULTILIGHT_1			1
#define	NJD_CNK_EASY_MULTILIGHT_2			2
#define	NJD_CNK_EASY_MULTILIGHT_3			3
#define	NJD_CNK_EASY_MULTILIGHT_4			4
#define	NJD_CNK_EASY_MULTILIGHT_5			5
#define	NJD_CNK_EASY_MULTILIGHT_6			6
#define	NJD_CNK_EASY_MULTILIGHT_7			7
#define	NJD_CNK_EASY_MULTILIGHT_ALL			0
#define	NJD_CNK_SIMPLE_MULTILIGHT_1			1
#define	NJD_CNK_SIMPLE_MULTILIGHT_2			2
#define	NJD_CNK_SIMPLE_MULTILIGHT_3			3
#define	NJD_CNK_SIMPLE_MULTILIGHT_4			4
#define	NJD_CNK_SIMPLE_MULTILIGHT_ALL		0
#define NJD_FFL_U         (BIT_15)
#define NJD_FFL_V         (BIT_14)
#define NJD_FCL_U         (BIT_13)
#define NJD_FCL_V         (BIT_12)
#define NJD_FFM_SHIFT      14
#define NJD_FFM_PS        (0<<NJD_FFM_SHIFT)
#define NJD_FFM_BF        (1<<NJD_FFM_SHIFT)
#define NJD_FFM_TF        (2<<NJD_FFM_SHIFT)
#define NJD_FFM_MASK      (0x3<<NJD_FFM_SHIFT)
#define NJD_FSS           (BIT_13)
#define NJD_TID_MASK      (~(NJD_FSS|NJD_FFM_MASK))
#define NJD_FW_SHIFT     8
#define NJD_FW_START    (0<<NJD_FW_SHIFT)
#define NJD_FW_MIDDLE   (1<<NJD_FW_SHIFT)
#define NJD_FW_END      (2<<NJD_FW_SHIFT)
#define NJD_FW_MASK     (0x2<<NJD_FW_SHIFT)
#define NJD_FV_SHIFT     8
#define NJD_FV_CONT     (0x80<<NJD_FV_SHIFT)
#define NJD_FST_SHIFT      8
#define NJD_FST_IL        (0x01<<NJD_FST_SHIFT)
#define NJD_FST_IS        (0x02<<NJD_FST_SHIFT)
#define NJD_FST_IA        (0x04<<NJD_FST_SHIFT)
#define NJD_FST_UA        (0x08<<NJD_FST_SHIFT)
#define NJD_FST_DB        (0x10<<NJD_FST_SHIFT)
#define NJD_FST_FL        (0x20<<NJD_FST_SHIFT)
#define NJD_FST_ENV       (0x40<<NJD_FST_SHIFT)
#define NJD_FST_MASK      (0xFF<<NJD_FST_SHIFT)
#define NJD_UFO_SHIFT      14
#define NJD_UFO_0         (0<<NJD_UFO_SHIFT)
#define NJD_UFO_1         (1<<NJD_UFO_SHIFT)
#define NJD_UFO_2         (2<<NJD_UFO_SHIFT)
#define NJD_UFO_3         (3<<NJD_UFO_SHIFT)
#define NJD_UFO_MASK      (0x3<<NJD_UFO_SHIFT)
typedef struct {
    Sint32            *vlist;
    Sint16            *plist;
    NJS_POINT3        center;
    Float                  r;
} NJS_CNK_MODEL;
typedef struct cnkobj {
    Uint32          evalflags;
    NJS_CNK_MODEL   *model;
    Float           pos[3];
    Angle           ang[3];
    Float           scl[3];
    struct cnkobj   *child;
    struct cnkobj   *sibling;
} NJS_CNK_OBJECT;
typedef    struct    {
    Sint32    clip;
    Float    sx;
    Float    sy;
    Float    ooz;
    NJS_POINT3    p;
    Uint32    dmy1;
    Sint32    vtype;
    NJS_VECTOR    v;
    union  {
        Uint32    argb[2];
        Float    inten[2];
    } col;
    Sint32    NinjaFlag;
    Sint32    UserFlag;
} NJS_CNK_VERTEX_BUF;
typedef    struct    {
    Float    x;
    Float    y;
    Float    ooz;
    Float    inten;
} NJS_CNK_EASY_BUF;
typedef    struct    {
    Float    z;
    Float    x;
    Float    y;
    Float    ooz;
    Float    inten;
    Float    spec;
    Float    nx;
    Float    ny;
} NJS_CNK_SIMPLE_BUF;
typedef    struct    {
    Float    z;
    Float    x;
    Float    y;
    Float    ooz;
    Float    a;
    Float    r;
    Float    g;
    Float    b;
} NJS_CNK_EASYMULTI_BUF;
void    njCnkSetEasyLight( Float x,Float y,Float z );
void    njCnkSetEasyLightIntensity( Float inten, Float ambient );
void    njCnkSetEasyLightColor( Float r, Float g, Float b );
void    njCnkEasyDrawModel( NJS_CNK_MODEL *model );
void    njCnkEasyDrawObject( NJS_CNK_OBJECT *model );
#define njCnkSetEasyLightC(x, y, z)     njCnkSetEasyLight((x), -1.f*(y), -1.f*(z))
void    njCnkEasyMultiDrawModel( NJS_CNK_MODEL *model );
void    njCnkEasyMultiDrawObject( NJS_CNK_OBJECT *model );
void    njCnkSetEasyMultiLight(Int num);
void    njCnkSetEasyMultiLightSwitch(Int light, Int flag);
void    njCnkSetEasyMultiAmbient(Float ar, Float ag, Float ab);
void    njCnkSetEasyMultiLightColor(Int light, Float lr, Float lg, Float lb);
void    njCnkSetEasyMultiLightVector(Float vx, Float vy, Float vz);
void    njCnkSetEasyMultiLightPoint(Int light, Float px, Float py, Float pz);
void    njCnkSetEasyMultiLightRange(Int light, Float nrange, Float frange);
void    njCnkSetEasyMultiLightMatrices(void);
void    njCnkSetSimpleLight( Float x,Float y,Float z );
void    njCnkSetSimpleLightIntensity( Float inten, Float ambient );
void    njCnkSetSimpleLightColor( Float r, Float g, Float b );
void    njCnkSimpleDrawModel( NJS_CNK_MODEL *model );
void    njCnkSimpleDrawObject( NJS_CNK_OBJECT *object );
#define njCnkSetSimpleLightC(x, y, z)     njCnkSetSimpleLight((x), -1.f*(y), -1.f*(z))
void    njCnkSimpleMultiDrawModel( NJS_CNK_MODEL *model );
void    njCnkSimpleMultiDrawObject( NJS_CNK_OBJECT *model );
void    njCnkSetSimpleMultiLight(Int num);
void    njCnkSetSimpleMultiLightSwitch(Int light, Int flag);
void    njCnkSetSimpleMultiAmbient(Float ar, Float ag, Float ab);
void    njCnkSetSimpleMultiLightColor(Int light, Float lr, Float lg, Float lb);
void    njCnkSetSimpleMultiLightVector(Float vx, Float vy, Float vz);
void    njCnkSetSimpleMultiLightPoint(Int light, Float px, Float py, Float pz);
void    njCnkSetSimpleMultiLightRange(Int light, Float nrange, Float frange);
void    njCnkSetSimpleMultiLightMatrices(void);
void    njCnkDrawModel( NJS_CNK_MODEL *model );
void    njCnkDrawObject( NJS_CNK_OBJECT *object );
void    njCnkModDrawModel( NJS_CNK_MODEL *model );
void    njCnkModDrawObject( NJS_CNK_OBJECT *object );
void    njCnkPreLightModel( NJS_CNK_MODEL *model );
void    njCnkPreLightObject( NJS_CNK_OBJECT *object );
void    njCnkEasyDrawModel2p( NJS_CNK_MODEL *model , Float *color);
void    njCnkEasyDrawObject2p( NJS_CNK_OBJECT *model , Float *color);
void    njCnkEasyMultiDrawModel2p( NJS_CNK_MODEL *model , Float *color);
void    njCnkEasyMultiDrawObject2p( NJS_CNK_OBJECT *model , Float *color);
void    njCnkSimpleDrawModel2p( NJS_CNK_MODEL *model , Float *color);
void    njCnkSimpleDrawObject2p( NJS_CNK_OBJECT *object , Float *color);
void    njCnkSimpleMultiDrawModel2p( NJS_CNK_MODEL *model , Float *color );
void    njCnkSimpleMultiDrawObject2p( NJS_CNK_OBJECT *model , Float *color );
void njSetCnkBlendMode(Uint32 attr);
void njCnkSetUvScroll( Float u, Float v);
#endif
