#ifndef _SG_BUP_H_
#define _SG_BUP_H_
#ifdef __cplusplus
extern "" {
#endif
#include <sg_xpt.h>
typedef struct {
	Uint16 year;
	Uint8 month;
	Uint8 day;
	Uint8 hour;
	Uint8 minute;
	Uint8 second;
	Uint8 dayofweek;
} BUS_TIME;
typedef struct {
	Uint8 volume[32];
	Uint16 total_blocks;
	Uint16 total_user_blocks;
	Uint16 free_blocks;
	Uint16 free_user_blocks;
	Uint16 total_exe_blocks;
	Uint16 free_exe_blocks;
	Uint16 block_size;
	Uint16 icon_no;
	BUS_TIME time;
} BUS_DISKINFO;
typedef struct {
	Uint32 filesize;
	Uint16 blocks;
	Uint8 type;
	Uint8 copyflag;
	Uint16 headerofs;
	BUS_TIME time;
} BUS_FILEINFO;
typedef struct {
	char vms_comment[18];
	char btr_comment[34];
	Uint8 game_name[16];
	void* icon_palette;
	void* icon_data;
	Uint16 icon_num;
	Uint16 icon_speed;
	void* visual_data;
	Uint16 visual_type;
	Uint16 reserved;
	void* save_data;
	Uint32 save_size;
} BUS_BACKUPFILEHEADER;
typedef struct {
	char vms_comment[16];
	Uint8 mono_icon[128];
	Uint16 color_icon_palette[16];
	Uint8 color_icon[512];
	Uint8 reserved[1024-16-128-544-4];
	Uint32 aligndata;
} BUS_VOLUMEICONFILE;
typedef void (*BU_INITCALLBACK)(void);
typedef Sint32 (*BU_COMPLETECALLBACK)(Sint32 drive, Sint32 op,
												Sint32 status, Uint32 param);
typedef Sint32 (*BU_PROGRESSCALLBACK)(Sint32 drive, Sint32 op,
												Sint32 count, Sint32 max);
Sint32 buInit(Sint32 capacity, Sint32 drives, void* work,
													BU_INITCALLBACK func);
Sint32 buExit(void);
Sint32 buSaveFile(Sint32 drive, const char* fname, const void* buf,
									Uint32 nblock, BUS_TIME* time, Uint32 flag);
Sint32 buSaveExecFile(Sint32 drive, const char* fname, const void* buf,
									Uint32 nblock, BUS_TIME* time, Uint32 flag);
Sint32 buLoadFile(Sint32 drive, const char* fname, void* buf, Uint32 nblock);
Sint32 buDeleteFile(Sint32 drive, const char* fname);
Sint32 buDeleteFileEx(Sint32 drive, const char** fname, Sint32 nfiles);
void buSetCompleteCallback(BU_COMPLETECALLBACK func);
void buSetProgressCallback(BU_PROGRESSCALLBACK func);
Sint32 buIsReady(Sint32 drive);
Sint32 buIsFormat(Sint32 drive);
Sint32 buGetDiskFree(Sint32 drive, Sint32 type);
Sint32 buGetFileInfo(Sint32 drive, const char* fname, BUS_FILEINFO* finfo);
Sint32 buGetFileSize(Sint32 drive, const char* fname);
Sint32 buIsExistFile(Sint32 drive, const char* fname);
Sint32 buStat(Sint32 drive);
Sint32 buGetLastError(Sint32 drive);
Sint32 buMountDisk(Sint32 drive, void* addr, Sint32 size);
Sint32 buUnmountDisk(Sint32 drive);
Sint32 buRewriteExecFile(Sint32 drive, const char* fname, const void* buf,
												Uint32 start, Uint32 nblock);
Sint32 buMakeBackupFileImage(void* buf, const BUS_BACKUPFILEHEADER* hdr);
Sint32 buCalcBackupFileSize(Uint32 inum, Uint32 vtype, Uint32 size);
Sint32 buAnalyzeBackupFileImage(BUS_BACKUPFILEHEADER* hdr, const void* buf);
void buSetCallbackParam(Uint32 param);
Sint32 buMount(Sint32 drive);
Sint32 buRemount(Sint32 drive);
Sint32 buUnmount(Sint32 drive);
Sint32 buGetDiskInfo(Sint32 drive, BUS_DISKINFO* info);
Sint32 buFindFirstFile(Sint32 drive, char* fname);
Sint32 buFindNextFile(Sint32 drive, char* fname);
Sint32 buFindFirstFileEx(Sint32 drive, char* fname, BUS_FILEINFO* finfo);
Sint32 buFindNextFileEx(Sint32 drive, char* fname, BUS_FILEINFO* finfo);
Sint32 buFindExecFile(Sint32 drive, char* fname);
Sint32 buSetFileAttr(Sint32 drive, const char* fname, Uint16 hdrofs,
															Uint8 copyflag);
Sint32 buFormatDisk(Sint32 drive, const Uint8* volume, Sint32 icon,
											const BUS_TIME* time, Uint32 flag);
Sint32 buRenameFile(Sint32 drive, const char* from, const char* to);
Sint32 buDefragDisk(Sint32 drive, void* work);
Sint32 buLoadFileEx(Sint32 drive, const char* fname, void* buf,
												Uint32 start, Uint32 nblock);
void buExecServer(void);
Uint32 buGetVersion(void);
void buSetPrintFunc(void (*func)(const char* str));
void buSetRetryCount(Sint32 count);
Sint32 buGetRetryCount(void);
Uint16 buCalcCRC(const void* buf, Uint32 size);
#define BUD_WORK_GAP 32
#define BUM_WORK_SIZE(_cap_, _max_) \
	(((_cap_ * _max_) * 512) + (BUD_WORK_GAP * _max_))
#define BUD_FLAG_VERIFY       0x80000000
#define BUD_FLAG_COPY(n)      (n & 0xff)
#define BUD_FLAG_COPYDISABLE  0x000000ff
#define BUD_CAPACITY_128KB   (1 + 1 +  13)
#define BUD_CAPACITY_256KB   (1 + 2 +  30)
#define BUD_CAPACITY_512KB   (1 + 4 +  60)
#define BUD_CAPACITY_1MB     (1 + 8 + 113)
#define BUD_USE_DRIVE_A1    (1 << 0)
#define BUD_USE_DRIVE_A2    (1 << 1)
#define BUD_USE_DRIVE_B1    (1 << 2)
#define BUD_USE_DRIVE_B2    (1 << 3)
#define BUD_USE_DRIVE_C1    (1 << 4)
#define BUD_USE_DRIVE_C2    (1 << 5)
#define BUD_USE_DRIVE_D1    (1 << 6)
#define BUD_USE_DRIVE_D2    (1 << 7)
#define BUD_USE_DRIVE_ALL   0xff
#define BUD_DRIVE_A1   0
#define BUD_DRIVE_A2   1
#define BUD_DRIVE_B1   2
#define BUD_DRIVE_B2   3
#define BUD_DRIVE_C1   4
#define BUD_DRIVE_C2   5
#define BUD_DRIVE_D1   6
#define BUD_DRIVE_D2   7
#define BUD_FILETYPE_NORMAL       0
#define BUD_FILETYPE_EXECUTABLE   1
#define BUD_STAT_READY       0x00000000
#define BUD_STAT_BUSY        0xffffffff
#define BUD_OP_NOP             0x00000000
#define BUD_OP_MOUNT           0x00000001
#define BUD_OP_UNMOUNT         0x00000002
#define BUD_OP_FORMATDISK      0x00000003
#define BUD_OP_CLOSEFILE       0x00000004
#define BUD_OP_READFILE        0x00000005
#define BUD_OP_WRITEFILE       0x00000006
#define BUD_OP_DELETEFILE      0x00000007
#define BUD_OP_RENAMEFILE      0x00000008
#define BUD_OP_DEFRAGDISK      0x00000009
#define BUD_OP_SETFILEATTR     0x0000000a
#define BUD_OP_LOADFILE        0x0000000b
#define BUD_OP_SAVEFILE        0x0000000c
#define BUD_OP_SAVEEXECFILE    0x0000000d
#define BUD_OP_LOADFILEEX      0x0000000e
#define BUD_OP_READIMAGE       0x0000000f
#define BUD_OP_WRITEIMAGE      0x00000010
#define BUD_OP_DELETEFILEEX    0x00000011
#define BUD_OP_CONNECT         0x00000012
#define BUD_OP_REMOVE          0x00000013
#define BUD_OP_REWRITEEXECFILE 0x00000014
#define BUD_CBRET_OK   0x00000000
#define BUD_ERR_OK              0x00000000
#define BUD_ERR_BUSY            0xffffffff
#define BUD_ERR_INVALID_PARAM   0xffffff00
#define BUD_ERR_ILLEGAL_DISK    0xffffff81
#define BUD_ERR_UNKNOWN_DISK    0xffffff83
#define BUD_ERR_NO_DISK         0xffffff01
#define BUD_ERR_UNFORMAT        0xffffff03
#define BUD_ERR_DISK_FULL       0xffffff04
#define BUD_ERR_FILE_NOT_FOUND  0xffffff05
#define BUD_ERR_FILE_EXIST      0xffffff06
#define BUD_ERR_CANNOT_OPEN     0xffffff07
#define BUD_ERR_CANNOT_CREATE   0xffffff08
#define BUD_ERR_EXECFILE_EXIST  0xffffff09
#define BUD_ERR_CANNOT_DELETE   0xffffff0a
#define BUD_ERR_ACCESS_DENIED   0xffffff0b
#define BUD_ERR_VERIFY          0xffffff10
#define BUD_ERR_WRITE_ERROR     0xffffff40
#define BUD_ERR_FILE_BROKEN     0xffffff41
#define BUD_ERR_BUPFILE_CRC     0xffffff20
#define BUD_ERR_BUPFILE_ILLEGAL 0xffffff21
#define BUD_ERR_GENERIC         0xffff0000
#define BUD_VISUALTYPE_NONE   0
#define BUD_VISUALTYPE_A      1
#define BUD_VISUALTYPE_B      2
#define BUD_VISUALTYPE_C      3
#ifdef __cplusplus
}
#endif
#endif
