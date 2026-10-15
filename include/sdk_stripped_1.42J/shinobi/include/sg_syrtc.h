#ifndef _SG_RTC_H_
#define _SG_RTC_H_
#define SYD_RTC_ERR_OK        (0)
#define SYD_RTC_ERR_FATAL     (-1)
#define SYD_RTC_STAT_ACTIVE   (0)
#define SYD_RTC_STAT_PASSIVE  (1)
#define SYD_RTC_FIRSTYEAR     (1950)
#define SYD_RTC_FIRSTMONTH    (1)
#define SYD_RTC_FIRSTDAY      (1)
#define SYD_RTC_FIRSTHOUR     (0)
#define SYD_RTC_FIRSTMINUTE   (0)
#define SYD_RTC_FIRSTSECOND   (0)
typedef struct _SYS_RTC_DATE {
    Uint16 year;
    Uint8  month;
    Uint8  day;
    Uint8  hour;
    Uint8  minute;
    Uint8  second;
    Uint8  dayofweek;
    Uint8  ageofmoon;
} SYS_RTC_DATE;
Sint32 syRtcInit( void );
void syRtcFinish( void );
void syRtcExecServer( void );
Sint32 syRtcGetDate( SYS_RTC_DATE *date );
Sint32 syRtcSetDate( const SYS_RTC_DATE *date );
void syRtcSetServerMode( const Sint32 mode );
Sint32 syRtcGetStat( void );
Sint32 syRtcCompareDate( const SYS_RTC_DATE *date1, const SYS_RTC_DATE *date2 );
void syRtcDateToCount( const SYS_RTC_DATE *date, Uint32 *count );
void syRtcCountToDate( const Uint32 count, SYS_RTC_DATE *date );
#endif
