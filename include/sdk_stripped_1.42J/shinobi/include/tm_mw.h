#ifndef	_TM_MW_H_
#define	_TM_MW_H_
typedef	struct tm_Tag{
	int nothing_in_here_yet;
}MWS_PLY_CPRM_TM;
void	mwPlyInitTM(void);
void	mwPlyFinishTM(void);
MWPLY	mwPlyCreateTM(MWS_PLY_CPRM_TM *cprm);
#endif

