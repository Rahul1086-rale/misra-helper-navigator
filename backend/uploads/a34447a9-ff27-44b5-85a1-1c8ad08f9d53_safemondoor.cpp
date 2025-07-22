/******************************************************************************
Filename:  		
				safemondoor.cpp

Description:  	
				Safety Monitoring class implementation for MC2X door circuit 
				 using SafeMon.h

Developed By:   
				ThyssenKrupp Elevator Software Development Team
                Atlanta, GA
________________________________________________________________________________

Proprietary - The data, drawings, and information contained in this document is
confidential ("Confidential Information") and the sole property of ThyssenKrupp
Elevator, and may not be reproduced, used, or disclosed without written permission
of an officer of ThyssenKrupp Elevator.  Recipient will maintain Confidential
Information in a secure location and restrict access to authorized personnel only.
_______________________________________________________________________________

Unless otherwise noted, the example companies, organizations, products, domain
names, e-mail addresses, logos, people, places and events depicted herein are
fictitious, and no association with any real company, organization, product,
domain name, e-mail address, logo, person, place or event is intended or should
be inferred.  Complying with all applicable copyright laws is the
responsibility of the user.  Without limiting the rights under copyright,
no part of this document may be reproduced, stored in or introduced into a
retrieval system, or transmitted in any form or by any means (electronic,
mechanical, photocopying, recording, or otherwise), or for any purpose, without
the express written permission of ThyssenKrupp Elevator.

ThyssenKrupp Elevator and/or others may have patents, patent applications,
trademarks, copyrights, or other intellectual property rights covering subject
matter in this document. Except as expressly provided in any written license
agreement from ThyssenKrupp Elevator, the furnishing of this document does not
grant any license or interest in or to these patents, trademarks, copyrights,
or other intellectual property.

Copyright 1996-2007 ThyssenKrupp Elevator Incorporated. All rights reserved.

$Revision: 67 $
$Date: 1/14/08 1:24p $
******************************************************************************/

// project includes
#include "adjust1.h"
#include "adjust2.h"
#include "adjust3.h"
#include "adjust4.h"
#include "b44.h"
#include "brake.h"
#include "cktmon.h"
#include "config.h"
#include "diagen.h"
#include "doorarb.h"  
#include "door.h"
#include "errrhdlr.h"
#include "hwwdog.h"
#include "firesvc.h"
#include "frghtdrv.h"    
#include "ioproc.h"
#include "iorouter.h"
#include "insphwac.h"    
#include "JbnfHdlr.h"
#include "lwrecal.h"
#include "motion.h"
#include "resident.h"
#include "runtime.h"
#include "safemon.h"       
#include "selector.h"
#include "safestr.h"      
#include "safetyck.h"
#include "startinterlck.h"
#include "texthdlr.h"
#include "tracdvr.h"


//-----------------------------------------------------------------------------
//	Definition
//-----------------------------------------------------------------------------

#define	DETAIL_LOGS				1
#define _ON						0x1	// on
#define	_FF						0x0	// off
#define _XX						0x2	// don't care
#define DONTCARE				_XX
#define SS_COND(TK,TKD,KT,KTD) 	((TK<<6)|(TKD<<4)|(KT<<2)|(KTD<<0))
#define SS_GET_TK(X)	((X>>6)&0x3)
#define SS_GET_TKD(X)	((X>>4)&0x3)
#define SS_GET_KT(X)	((X>>2)&0x3)
#define SS_GET_KTD(X)	((X>>0)&0x3)

#define BRG_COND(A,B,C,D,E,F,G,H,I,J)	\
	((A<<(2*9))|(B<<(2*8))|(C<<(2*7))|(D<<(2*6))|(E<<(2*5))|\
	 (F<<(2*4))|(G<<(2*3))|(H<<(2*2))|(I<<(2*1))|(J<<(2*0)))

#define	IS_BRIDGE(X)	(((DONTCARE&X)==DONTCARE)?0:X)
#define	GET_BRG_1(X) 	((X>>(2*9))&0x3)
#define	GET_BRG_2(X) 	((X>>(2*8))&0x3)
#define	GET_BRG_3(X) 	((X>>(2*7))&0x3)
#define	GET_BRG_4(X) 	((X>>(2*6))&0x3)
#define	GET_BRG_5(X) 	((X>>(2*5))&0x3)
#define	GET_BRG_6(X) 	((X>>(2*4))&0x3)
#define	GET_BRG_7(X) 	((X>>(2*3))&0x3)
#define	GET_BRG_8(X) 	((X>>(2*2))&0x3)
#define	GET_BRG_9(X) 	((X>>(2*1))&0x3)
#define	GET_BRG_A(X) 	((X>>(2*0))&0x3)
//-----------------------------------------------------------------------------
typedef struct
{
	uint16 safetyString;
	uint32 bridgeCond;
} DOOR_SS_STAT;

typedef struct
{
	DOOR_SS_STAT *ss;
	bool8 bK39;	// 1:Closed, 0:Open
	bool8 bK9;	// 1:Closed, 0:Open
	bool8 bK10;	// 1:Closed, 0:Open
} DOOR_SS_CHECK;

typedef struct
{
	DOOR_SS_CHECK *ss;
	uint8 FDOL;
	uint8 RDOL;
} DOOR_STAT_CHECK;
const char *DStat( uint8 val )
{
	switch ( val ) 
	{
		case _ON://						0x1	// on
			return "ON";
		case _FF://						0x0	// off
			return "OF";
		case _XX://						0x2	// don't care
			return "XX";
	}
	return "??";
}
void debugPrintDOOR_SS_STAT(DOOR_SS_STAT *ss , uint32 Cond)
{
#if	DETAIL_LOGS				
	DPRINTF(LOG_CAR_MOTION, "TK:%s,TKD:%s,KT:%s,KTD:%s "
			"Cond[%s,%s,%s,%s,%s,%s,%s,%s,%s,%s] %08x\n", 
		DStat(SS_GET_TK(ss->safetyString)),DStat(SS_GET_TKD(ss->safetyString)),
		DStat(SS_GET_KT(ss->safetyString)),DStat(SS_GET_KTD(ss->safetyString)),
		DStat(GET_BRG_1(ss->bridgeCond)),  DStat(GET_BRG_2(ss->bridgeCond)),
		DStat(GET_BRG_3(ss->bridgeCond)),  DStat(GET_BRG_4(ss->bridgeCond)),
		DStat(GET_BRG_5(ss->bridgeCond)),  DStat(GET_BRG_6(ss->bridgeCond)),
		DStat(GET_BRG_7(ss->bridgeCond)),  DStat(GET_BRG_8(ss->bridgeCond)),
		DStat(GET_BRG_9(ss->bridgeCond)),  DStat(GET_BRG_A(ss->bridgeCond)), 
		Cond);
#endif
}
void debugPrintDOOR_STAT_CHECK(DOOR_STAT_CHECK *ss )
{
#if	DETAIL_LOGS				
	DPRINTF(LOG_CAR_MOTION, "STAT_CHECK[FDOL:%d, RDOL:%d]\n", 
			ss->FDOL, ss->RDOL);
#endif
}
void debugPrintDOOR_SS_CHECK(DOOR_SS_CHECK *ss )
{
#if	DETAIL_LOGS				
	DPRINTF(LOG_CAR_MOTION, "SS_CHECK[K39:%s, K9:%s, K10:%s]\n", 
			DStat(ss->bK39), DStat(ss->bK9), DStat(ss->bK10));
#endif
}

//-----------------------------------------------------------------------------
//** Front and rear open at the same time.
static DOOR_SS_STAT	ssCheckFDOLRDOL_COO[] = //TSO  K39:Clos8 K9:Open KlO:Open
{
	// safety string 		  BridgeCondition
    {SS_COND(_FF,_FF,_FF,_ON), BRG_COND(_FF,_FF,_FF,_ON,_ON,_ON,_FF,_ON,_FF,_FF)},
    {SS_COND(_FF,_FF,_ON,_ON), BRG_COND(_FF,_FF,_ON,_ON,_ON,_FF,_FF,_FF,_FF,_ON)},
    {SS_COND(_FF,_ON,_FF,_ON), BRG_COND(_FF,_ON,_FF,_ON,_FF,_FF,_FF,_FF,_ON,_FF)},
    {SS_COND(_FF,_ON,_ON,_ON), BRG_COND(_FF,_ON,_ON,_ON,_FF,_FF,_FF,_ON,_ON,_ON)},
    {SS_COND(_ON,_FF,_FF,_ON), BRG_COND(_ON,_FF,_FF,_ON,_FF,_FF,_ON,_FF,_FF,_FF)},
    {SS_COND(_ON,_FF,_ON,_ON), BRG_COND(_ON,_FF,_ON,_ON,_FF,_ON,_ON,_FF,_FF,_ON)},
    {SS_COND(_ON,_ON,_FF,_ON), BRG_COND(_ON,_ON,_FF,_ON,_ON,_FF,_ON,_FF,_ON,_FF)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end

};
static DOOR_SS_STAT	ssCheckFDOLRDOL_OOO[] = //TSO  K39:Open K9:Open KlO:Open
{
    {SS_COND(_FF,_FF,_FF,_FF), BRG_COND(_FF,_FF,_FF,_FF,_ON,_ON,_ON,_ON,_ON,_ON)},
    {SS_COND(_FF,_FF,_FF,_ON), BRG_COND(_FF,_FF,_FF,_ON,_ON,_ON,_FF,_ON,_FF,_FF)},
    {SS_COND(_FF,_FF,_ON,_FF), BRG_COND(_FF,_FF,_ON,_FF,_ON,_FF,_ON,_FF,_ON,_FF)},
    {SS_COND(_FF,_FF,_ON,_ON), BRG_COND(_FF,_FF,_ON,_ON,_FF,_FF,_FF,_FF,_FF,_ON)},
    {SS_COND(_FF,_ON,_FF,_FF), BRG_COND(_FF,_ON,_FF,_FF,_FF,_ON,_ON,_FF,_FF,_ON)},
    {SS_COND(_FF,_ON,_FF,_ON), BRG_COND(_FF,_ON,_FF,_ON,_FF,_FF,_FF,_FF,_ON,_FF)},
    {SS_COND(_FF,_ON,_ON,_FF), BRG_COND(_FF,_ON,_ON,_FF,_FF,_FF,_FF,_FF,_FF,_FF)},
    {SS_COND(_FF,_ON,_ON,_ON), BRG_COND(_FF,_ON,_ON,_ON,_FF,_FF,_FF,_ON,_ON,_ON)},
    {SS_COND(_ON,_FF,_FF,_FF), BRG_COND(_ON,_FF,_FF,_FF,_FF,_FF,_FF,_ON,_ON,_ON)},
    {SS_COND(_ON,_FF,_FF,_ON), BRG_COND(_ON,_FF,_FF,_ON,_FF,_FF,_ON,_FF,_FF,_FF)},
    {SS_COND(_ON,_FF,_ON,_FF), BRG_COND(_ON,_FF,_ON,_FF,_FF,_ON,_FF,_FF,_FF,_FF)},
    {SS_COND(_ON,_FF,_ON,_ON), BRG_COND(_ON,_FF,_ON,_ON,_FF,_ON,_ON,_FF,_FF,_ON)},
    {SS_COND(_ON,_ON,_FF,_FF), BRG_COND(_ON,_ON,_FF,_FF,_ON,_FF,_FF,_FF,_FF,_FF)},
    {SS_COND(_ON,_ON,_FF,_ON), BRG_COND(_ON,_ON,_FF,_ON,_ON,_FF,_ON,_FF,_ON,_FF)},
    {SS_COND(_ON,_ON,_ON,_FF), BRG_COND(_ON,_ON,_ON,_FF,_ON,_ON,_FF,_ON,_FF,_FF)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_STAT	ssCheckFDOLRDOL_OCO[] = //TSO  K39:Open K9:close KlO:Open
{
    {SS_COND(_ON,_FF,_FF,_FF), BRG_COND(_ON,_ON,_ON,_ON,_FF,_FF,_FF,_ON,_ON,_ON)},
    {SS_COND(_ON,_FF,_FF,_ON), BRG_COND(_ON,_FF,_FF,_FF,_FF,_FF,_ON,_ON,_FF,_FF)},
    {SS_COND(_ON,_FF,_ON,_FF), BRG_COND(_ON,_FF,_ON,_FF,_FF,_ON,_FF,_FF,_FF,_FF)},
    {SS_COND(_ON,_FF,_ON,_ON), BRG_COND(_ON,_FF,_ON,_ON,_FF,_ON,_ON,_FF,_FF,_ON)},
    {SS_COND(_ON,_ON,_FF,_FF), BRG_COND(_ON,_ON,_FF,_FF,_ON,_FF,_FF,_FF,_FF,_FF)},
    {SS_COND(_ON,_ON,_FF,_ON), BRG_COND(_ON,_ON,_FF,_ON,_ON,_FF,_ON,_FF,_ON,_FF)},
    {SS_COND(_ON,_ON,_ON,_FF), BRG_COND(_ON,_ON,_ON,_FF,_ON,_ON,_FF,_ON,_FF,_FF)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_STAT	ssCheckFDOLRDOL_OOC[] = //TSO  K39:Open K9:open KlO:closed
{
    {SS_COND(_FF,_FF,_ON,_FF), BRG_COND(_ON,_ON,_ON,_ON,_ON,_FF,_ON,_FF,_ON,_FF)},
    {SS_COND(_FF,_FF,_ON,_ON), BRG_COND(_FF,_FF,_ON,_ON,_FF,_FF,_FF,_FF,_FF,_ON)},
    {SS_COND(_FF,_ON,_ON,_FF), BRG_COND(_FF,_ON,_ON,_FF,_FF,_FF,_FF,_ON,_FF,_FF)},
    {SS_COND(_FF,_ON,_ON,_ON), BRG_COND(_FF,_ON,_ON,_ON,_FF,_FF,_FF,_ON,_ON,_ON)},
    {SS_COND(_ON,_FF,_ON,_FF), BRG_COND(_ON,_FF,_ON,_FF,_FF,_ON,_FF,_FF,_FF,_FF)},
    {SS_COND(_ON,_FF,_ON,_ON), BRG_COND(_ON,_FF,_ON,_ON,_FF,_ON,_ON,_FF,_FF,_ON)},
    {SS_COND(_ON,_ON,_ON,_FF), BRG_COND(_ON,_ON,_ON,_FF,_ON,_ON,_FF,_ON,_FF,_FF)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_CHECK ssCheckFDOLRDOL[] = 
{
	// Status              K39, K9, K10
	{ ssCheckFDOLRDOL_COO, _ON, _FF, _FF},  //_ON:CLOSE, _FF:OPEN	
	{ ssCheckFDOLRDOL_OOO, _FF, _FF, _FF},  //_ON:CLOSE, _FF:OPEN	
	{ ssCheckFDOLRDOL_OCO, _FF, _ON, _FF},  //_ON:CLOSE, _FF:OPEN	
	{ ssCheckFDOLRDOL_OOC, _FF, _FF, _ON},  //_ON:CLOSE, _FF:OPEN	
	{NULL,	                _XX,  _XX, _XX }
};

//* Front open;rear closed.
static DOOR_SS_STAT	ssCheckFDOLRDCL_COO[] = //TSO  K39:close K9:open KlO:open
{
    {SS_COND(_FF,_FF,_ON,_ON), BRG_COND(_FF,_FF,_ON,_ON,_XX,_FF,_FF,_FF,_FF,_XX)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_XX,_ON,_ON,_ON,_ON,_XX)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_STAT	ssCheckFDOLRDCL_OOO[] = //TSO  K39:open K9:open KlO:open
{
    {SS_COND(_FF,_FF,_FF,_FF), BRG_COND(_FF,_FF,_FF,_FF,_XX,_ON,_ON,_ON,_ON,_XX)},
    {SS_COND(_FF,_FF,_ON,_ON), BRG_COND(_FF,_FF,_ON,_ON,_XX,_FF,_FF,_FF,_FF,_XX)},
    {SS_COND(_ON,_ON,_FF,_FF), BRG_COND(_ON,_ON,_FF,_FF,_XX,_FF,_FF,_FF,_FF,_XX)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_XX,_ON,_ON,_ON,_ON,_XX)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_STAT	ssCheckFDOLRDCL_OCO[] = //TSO  K39:open K9:close KlO:open
{
    {SS_COND(_ON,_ON,_FF,_FF), BRG_COND(_ON,_ON,_FF,_FF,_XX,_FF,_FF,_FF,_FF,_XX)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_XX,_ON,_ON,_ON,_ON,_XX)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_STAT	ssCheckFDOLRDCL_OOC[] = //TSO  K39:open K9:open KlO:close
{
    {SS_COND(_FF,_FF,_ON,_ON), BRG_COND(_FF,_FF,_ON,_ON,_XX,_FF,_FF,_FF,_FF,_XX)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_ON,_ON,_ON,_ON,_XX,_ON,_ON,_ON,_ON,_XX)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_CHECK ssCheckFDOLRDCL[] = 
{
	// Status              K39, K9, K10
	{ssCheckFDOLRDCL_COO,	_ON,  _FF, _FF }, //_ON:CLOSE, _FF:OPEN	
	{ssCheckFDOLRDCL_OOO,	_FF,  _FF, _FF }, //_ON:CLOSE, _FF:OPEN	
	{ssCheckFDOLRDCL_OCO,	_FF,  _ON, _FF }, //_ON:CLOSE, _FF:OPEN	
	{ssCheckFDOLRDCL_OOC,	_FF,  _FF, _ON }, //_ON:CLOSE, _FF:OPEN	
	{NULL,	                _XX,  _XX, _XX }
};

// Front closed;rear open.
static DOOR_SS_STAT	ssCheckFDCLRDOL_COO[] = // //TSO  K39:close K9:open KlO:open
{
    {SS_COND(_ON,_FF,_FF,_ON), BRG_COND(_XX,_FF,_FF,_ON,_FF,_FF,_ON,_XX,_FF,_FF)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_XX,_ON,_ON,_ON,_ON,_ON,_ON,_XX,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};

static DOOR_SS_STAT	ssCheckFDCLRDOL_OOO[] = // //TSO  K39:open K9:open KlO:open
{
    {SS_COND(_ON,_FF,_FF,_FF), BRG_COND(_XX,_FF,_FF,_FF,_FF,_FF,_FF,_XX,_ON,_ON)},
    {SS_COND(_ON,_FF,_FF,_ON), BRG_COND(_XX,_FF,_FF,_ON,_FF,_FF,_ON,_XX,_ON,_ON)},
    {SS_COND(_ON,_ON,_ON,_FF), BRG_COND(_XX,_ON,_ON,_FF,_ON,_ON,_FF,_XX,_ON,_ON)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_XX,_ON,_ON,_ON,_ON,_ON,_ON,_XX,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};
static DOOR_SS_STAT	ssCheckFDCLRDOL_OCO[] = // //TSO  K39:open K9:close KlO:open
{
    {SS_COND(_ON,_FF,_FF,_FF), BRG_COND(_XX,_FF,_FF,_FF,_FF,_FF,_FF,_XX,_ON,_ON)},
    {SS_COND(_ON,_FF,_FF,_ON), BRG_COND(_XX,_FF,_FF,_ON,_FF,_FF,_ON,_XX,_ON,_ON)},
    {SS_COND(_ON,_ON,_ON,_FF), BRG_COND(_XX,_ON,_ON,_FF,_ON,_ON,_FF,_XX,_ON,_ON)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_XX,_ON,_ON,_ON,_ON,_ON,_ON,_XX,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};
static DOOR_SS_STAT	ssCheckFDCLRDOL_OOC[] = // //TSO  K39:open K9:open KlO:close
{
    {SS_COND(_ON,_ON,_ON,_FF), BRG_COND(_XX,_ON,_ON,_FF,_ON,_ON,_FF,_XX,_ON,_ON)},
    {SS_COND(_ON,_ON,_ON,_ON), BRG_COND(_XX,_ON,_ON,_ON,_ON,_ON,_ON,_XX,_ON,_ON)},
    {0xFFFF,                   0xFFFFFFFF}// end
};
static DOOR_SS_CHECK ssCheckFDCLRDOL[] = 
{
	// Status              K39, K9, K10
	{ssCheckFDCLRDOL_COO,	_ON,  _FF, _FF }, //_ON:CLOSE, _FF:OPEN	
	{ssCheckFDCLRDOL_OOO,	_FF,  _FF, _FF }, //_ON:CLOSE, _FF:OPEN	
	{ssCheckFDCLRDOL_OCO,	_FF,  _ON, _FF }, //_ON:CLOSE, _FF:OPEN	
	{ssCheckFDCLRDOL_OOC,	_FF,  _FF, _ON }, //_ON:CLOSE, _FF:OPEN	
	{NULL,	                _XX,  _XX, _XX }
};

//* only front door.
static DOOR_SS_STAT	ssCheckFDCLRDOL_CXX[] = //TSO  K39:close 
{
	{ SS_COND(_FF,_XX,_ON,_XX), BRG_COND(_FF,_FF,_ON,_XX,_XX,_XX,_XX,_XX,_XX,_XX)},
	{ SS_COND(_ON,_XX,_ON,_XX), BRG_COND(_ON,_ON,_ON,_XX,_XX,_XX,_XX,_XX,_XX,_XX)},
	{ 0xFFFF,                   0xFFFFFFFF}
};

static DOOR_SS_STAT	ssCheckFDCLRDOL_OXX[] = //TSO  K39:open 
{
	{ SS_COND(_FF,_XX,_FF,_XX), BRG_COND(_FF,_ON,_FF,_XX,_XX,_XX,_XX,_XX,_XX,_XX)}, 
	{ SS_COND(_FF,_XX,_ON,_XX), BRG_COND(_FF,_FF,_ON,_XX,_XX,_XX,_XX,_XX,_XX,_XX)},
	{ SS_COND(_ON,_XX,_FF,_XX), BRG_COND(_ON,_FF,_FF,_XX,_XX,_XX,_XX,_XX,_XX,_XX)},
	{ SS_COND(_ON,_XX,_ON,_XX), BRG_COND(_ON,_ON,_ON,_XX,_XX,_XX,_XX,_XX,_XX,_XX)},
	{ 0xFFFF,                   0xFFFFFFFF}
};

static DOOR_SS_CHECK ssCheckFDCLRDOLSingle[] = 
{
	// Status              K39, K9, K10
	{ssCheckFDCLRDOL_CXX,	_ON,  _XX, _XX },	//_ON:CLOSE, _FF:OPEN	
	{ssCheckFDCLRDOL_OXX,	_FF,  _XX, _XX },	//_ON:CLOSE, _FF:OPEN
	{NULL,	                _XX,  _XX, _XX }
};

static DOOR_STAT_CHECK ssDoubleDoor[] = 
{
	//                    Front, Rear
	{ssCheckFDOLRDOL, _ON, _ON },	// On:Open, FF:Closed
	{ssCheckFDOLRDCL, _ON, _FF },
	{ssCheckFDCLRDOL, _FF, _ON },
	{ NULL, _XX, _XX}	
};

static DOOR_STAT_CHECK ssSingleDoor[] = 
{
	//                    Front, Rear
	{ ssCheckFDCLRDOLSingle, _ON, _XX},	// _ON:CLOSE, _FF:OPEN
	{ NULL, _XX, _XX}
};
//-----------------------------------------------------------------------------
//-----------------------------------------------------------------------------
bool8 SafeMon::isCarDoorBridged = FALSE;
bool8 SafeMon::isHallDoorBridged = FALSE;
	
bool8 SafeMon::MC2XDoorTestEnabled()
{ 
	return TRUE;
}

bool8 SafeMon::MC2XDoorTestNow()
{	 
	return TRUE;
}

enum 
{ 
	CDC_IDLE  = 0,				// 0 				// 0 
	CDC_ARM_TEST, 				// 1
	CDC_ARM_WAIT,				// 2 
	CDC_ARM_CHECK,				// 3 
	CDC_ARM_ERROR_DETECTED,		// 4 
	CDC_ARM_RETRY_WAIT,			// 5 
	CDC_ARM_TEST_PASSED,		// 6 
	CDC_ABORT,					// 7
	CDC_END
};

#if 1
bool8 SafeMon::MC2XDoorTestOK()
{
	uint8 i;
	static TenthsTimer delay;
	static DOOR_SS_CHECK *ssCheck = NULL;
	static DOOR_SS_CHECK *ssCur = NULL;
	#define DONTCARE_MASK	0xAAAAAAAA
	static uint32 Cond = ~DONTCARE_MASK;
	static bool8 testOkay = TRUE;
	static uint8 cdc_state = CDC_IDLE;

	uint8 FDState = _XX, RDState = _XX;
	static uint8 tFDState = _XX, tRDState = _XX;	// test condition..

	DOOR_STAT_CHECK *ssDoor = ( DoorArb::GetDoorTypeRear() ) 
		? ssDoubleDoor : ssSingleDoor;

	if ( FDoor.GetDoorOnlineAndReady() )
	{
		if (FDoor.GetDOL() && !FDoor.GetDCL()) 
			FDState = _ON;
		else 
			FDState = _FF;
	}
	if ( DoorArb::GetDoorTypeRear() )
	{
		if ( RDoor.GetDoorOnlineAndReady() )
		{
			if (RDoor.GetDOL() && !RDoor.GetDCL()) 
				RDState = _ON;
			else 
				RDState = _FF;
		}	
	} 

	static uint8 pcdc_state = 0;

	switch ( cdc_state )
	{
		case CDC_ABORT:
			TracDvr::SetDCTR (FALSE);
			oDK9 = FALSE;
			oDK10 = FALSE;
			cdc_state = CDC_IDLE;
			// break; intentionally commented out.
	
		case CDC_IDLE:
			if (( (((FDState == _ON) || (RDState == _ON)) && 
							(ssCheck == NULL))) && SafeStr::GetSRFD())
			{
				i = 0;
				while(ssDoor[i].ss ) 
				{
					if (
						(ssDoor[i].FDOL==FDState) && 
						((ssDoor[i].RDOL==RDState) || (ssDoor[i].RDOL==_XX))
					)
					{
						if ( ssCheck != ssDoor[i].ss ) 
						{
#if	DETAIL_LOGS				
							DPRINTF(LOG_CAR_MOTION, 
									">* ssDoor [%d] FD:%s RD:%s ssCheck=%d\n", 
									i, DStat(FDState), DStat( RDState), 
									ssCheck);
#endif

							cdc_state = CDC_ARM_TEST;
							ssCheck = ssDoor[i].ss;
							ssCur = ssCheck;
							tFDState = FDState;
							tRDState = RDState;
							Cond = ~DONTCARE_MASK;
							break;
						}
					}
					i++;
				}
			}
			else if ( ( tFDState != FDState ) || ( tRDState != RDState ))
			{
#if	DETAIL_LOGS				
				DPRINTF(LOG_CAR_MOTION, ">ssCheck = NULL? %d %d %d %d \n", 
						tFDState , FDState ,tRDState , RDState );
#endif
				tFDState = FDState;
				tRDState = RDState;
				ssCheck = NULL;	// reset..
			}

			break;

		case CDC_ARM_TEST:
			if (((tFDState != FDState ) || ( tRDState != RDState)) && 
					SafeStr::GetSRFD())
			{
#if	DETAIL_LOGS				
				DPRINTF(LOG_CAR_MOTION, ">Cancel test F[%d->%d] R[%d->%d]\n", 
						tFDState, FDState, tRDState,RDState);
#endif
				cdc_state = CDC_ABORT;
			} 
			else if ( ssCur )
			{
				if ( ssCur->ss ) 
				{
					debugPrintDOOR_SS_CHECK(ssCur);
	
					TracDvr::SetDCTR ((ssCur->bK39==_FF)?TRUE:FALSE);
					if ( ssCur->bK9 != _XX )
						oDK9 = (ssCur->bK9==_ON)?TRUE:FALSE;
					if ( ssCur->bK10 != _XX )
						oDK10 = (ssCur->bK10==_ON)?TRUE:FALSE;
	
					cdc_state = CDC_ARM_WAIT;
					#define CDC_ARM_WAIT_TIME	3
					delay.Init(CDC_ARM_WAIT_TIME);		// 0.1
				}
				else 
					cdc_state = CDC_ABORT;	// sanity check..
			}
			else 
				cdc_state = CDC_ABORT;
			break;

		case CDC_ARM_WAIT:
			if (((tFDState != FDState ) || ( tRDState != RDState)) && 
					SafeStr::GetSRFD())
			{
#if	DETAIL_LOGS				
				DPRINTF(LOG_CAR_MOTION, 
						">Cancel the test F[%d->%d] R[%d->%d](1)\n", 
						tFDState, FDState, tRDState,RDState);
#endif
				cdc_state = CDC_ABORT;

			} 
			else if (delay.Finished())
			{
				cdc_state = CDC_ARM_CHECK;
			}
			break;

		case CDC_ARM_CHECK:
			DOOR_SS_STAT *dss = ssCur->ss;
			if (((tFDState != FDState ) || ( tRDState != RDState)) && SafeStr::GetSRFD())
			{
#if	DETAIL_LOGS				
				DPRINTF(LOG_CAR_MOTION, ">Cancel the test F[%d->%d] R[%d->%d](2)\n", tFDState, FDState, tRDState,RDState);
#endif
				cdc_state = CDC_ABORT;
				break;
			} 
#if	DETAIL_LOGS				
			DPRINTF(LOG_CAR_MOTION, "  *TK: %d, TKD:%d, KT:%d, KTD:%d\n", 
				SafeStr::GetSAF3Raw(), SafeStr::GetSAF3RRaw(),
				SafeStr::GetSAF4Raw() , SafeStr::GetSAF4RRaw());
#endif
					
			if ( dss ) 
			{
				i = 0;
				while ( dss[i].safetyString  != 0xFFFF )
				{
 					if (
						((SS_GET_TK(dss[i].safetyString)&DONTCARE)  || 
						 (SS_GET_TK(dss[i].safetyString) == SafeStr::GetSAF3Raw())) && 
 						((SS_GET_TKD(dss[i].safetyString)&DONTCARE) || 
						 (SS_GET_TKD(dss[i].safetyString) == SafeStr::GetSAF3RRaw())) && 
 						((SS_GET_KT(dss[i].safetyString)&DONTCARE)  || 
						 (SS_GET_KT(dss[i].safetyString) == SafeStr::GetSAF4Raw())) && 
 						((SS_GET_KTD(dss[i].safetyString)&DONTCARE) || 
						 (SS_GET_KTD(dss[i].safetyString) == SafeStr::GetSAF4RRaw()))
					)
					{
						Cond &= dss[i].bridgeCond;
						Cond |= (DONTCARE_MASK & dss[i].bridgeCond);
#if	DETAIL_LOGS				
						DPRINTF(LOG_CAR_MOTION, "***TK: %d, TKD:%d, KT:%d, KTD:%d\n", 
							SS_GET_TK(dss[i].safetyString) , SS_GET_TKD(dss[i].safetyString),
							SS_GET_KT(dss[i].safetyString) , SS_GET_KTD(dss[i].safetyString));
#endif


						debugPrintDOOR_SS_STAT(&dss[i], Cond);
						break;
					}
					i++;
				}
				ssCur++;
			}
			// clean up.
			TracDvr::SetDCTR (FALSE);
			oDK9 = FALSE;
			oDK10 = FALSE;

			if ( ssCur->ss ) 
			{
				cdc_state = CDC_ARM_TEST;
			}
			else 
			{
				uint16 result = 0;
				if(IS_BRIDGE(GET_BRG_1(Cond))) 
				{
					isCarDoorBridged = TRUE;
					ErrrHdlr::PutError( DOOR_BRIDGED_1, DOOR_BRIDGED_1_MSG);
					result |= (1<<0);                                 
				}
				if(IS_BRIDGE(GET_BRG_2(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_2, DOOR_BRIDGED_2_MSG);
					result |= (1<<1);                                 
				}
				if(IS_BRIDGE(GET_BRG_3(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_3, DOOR_BRIDGED_3_MSG);
					result |= (1<<2);                                 
				}
				if(IS_BRIDGE(GET_BRG_4(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_4, DOOR_BRIDGED_4_MSG);
					result |= (1<<3);                                 
				}
				if(IS_BRIDGE(GET_BRG_5(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_5, DOOR_BRIDGED_5_MSG);
					isHallDoorBridged = TRUE;
					result |= (1<<4);                                 
				}
				if(IS_BRIDGE(GET_BRG_6(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_6, DOOR_BRIDGED_6_MSG);
					result |= (1<<5);                                 
				}
				if(IS_BRIDGE(GET_BRG_7(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_7, DOOR_BRIDGED_7_MSG);
					result |= (1<<6);                                 
				}
				if(IS_BRIDGE(GET_BRG_8(Cond)))                              
				{
					isCarDoorBridged = TRUE;
					ErrrHdlr::PutError( DOOR_BRIDGED_8, DOOR_BRIDGED_8_MSG);
					result |= (1<<7);                                 
				}
				if(IS_BRIDGE(GET_BRG_9(Cond)))                              
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_9, DOOR_BRIDGED_9_MSG);
					result |= (1<<8);
				}

				if(IS_BRIDGE(GET_BRG_A(Cond))) 
				{
					ErrrHdlr::PutError( DOOR_BRIDGED_10, DOOR_BRIDGED_10_MSG);
					isHallDoorBridged = TRUE;
					result |= (1<<9);
				}
#if	DETAIL_LOGS				
				if ( result ) 
					DPRINTF(LOG_CAR_MOTION, "RESULT = %04x\n", result );
#endif
				if ( SafeStr::GetSRFD())
				{
					cdc_state = ( result ) 
						? CDC_ARM_ERROR_DETECTED
						: CDC_ARM_TEST_PASSED;
				}
				else 
					cdc_state = CDC_ABORT;
			}
			break;
		case CDC_ARM_ERROR_DETECTED:
			// we do not want to recover from the failure once detected.
			testOkay = FALSE;			
			#define CDC_RETRY_WAIT_TIME	20	// *0.1 sec	= 2 sec.
			delay.Init(CDC_RETRY_WAIT_TIME);
			cdc_state = CDC_ARM_RETRY_WAIT;
			break;

		case CDC_ARM_RETRY_WAIT:
			if ( delay.Finished())
			{
				ssCheck = NULL;
				cdc_state = CDC_IDLE;
			}
			break;

		case CDC_ARM_TEST_PASSED:
			testOkay = TRUE;
			isCarDoorBridged = FALSE;
			isHallDoorBridged = FALSE;
			cdc_state = CDC_IDLE;
			break;
	}
	if ( pcdc_state != cdc_state )
	{
#if	DETAIL_LOGS				
		DPRINTF(LOG_CAR_MOTION, "STATE -> %d\n", cdc_state );
#endif
		pcdc_state = cdc_state;
	}
	return testOkay;
}
#else
// TODO:for more testing.. will be deleted later..
bool8 SafeMon::MC2XDoorTestOK()	
{
	return TRUE;
}
#endif

void SafeMon::MC2XDoorFaultResponse()
{
	
}

bool8 SafeMon::MC2XDoorTryReset()
{	
	return TRUE;
}

