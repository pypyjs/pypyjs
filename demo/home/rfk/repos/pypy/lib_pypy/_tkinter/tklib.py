# C bindings with libtcl and libtk.

from cffi import FFI

tkffi = FFI()

tkffi.cdef("""
char *get_tk_version();
char *get_tcl_version();
#define TCL_READABLE ...
#define TCL_WRITABLE ...
#define TCL_EXCEPTION ...
#define TCL_ERROR ...
#define TCL_OK ...

#define TCL_LEAVE_ERR_MSG ...
#define TCL_GLOBAL_ONLY ...
#define TCL_EVAL_DIRECT ...
#define TCL_EVAL_GLOBAL ...

typedef unsigned short Tcl_UniChar;
typedef ... Tcl_Interp;
typedef ...* Tcl_ThreadId;
typedef ...* Tcl_Command;

typedef struct Tcl_ObjType {
    char *name;
    ...;
} Tcl_ObjType;
typedef struct Tcl_Obj {
    char *bytes;
    int length;
    Tcl_ObjType *typePtr;
    union {                     /* The internal representation: */
        long longValue;         /*   - an long integer value. */
        double doubleValue;     /*   - a double-precision floating value. */
        struct {                /*   - internal rep as two pointers. */
            void *ptr1;
            void *ptr2;
        } twoPtrValue;
    } internalRep;
    ...;
} Tcl_Obj;

Tcl_Interp *Tcl_CreateInterp();
void Tcl_DeleteInterp(Tcl_Interp* interp);
int Tcl_Init(Tcl_Interp* interp);
int Tk_Init(Tcl_Interp* interp);

void Tcl_Free(char* ptr);

const char *Tcl_SetVar(Tcl_Interp* interp, const char* varName, const char* newValue, int flags);
const char *Tcl_SetVar2(Tcl_Interp* interp, const char* name1, const char* name2, const char* newValue, int flags);
const char *Tcl_GetVar(Tcl_Interp* interp, const char* varName, int flags);
Tcl_Obj *Tcl_SetVar2Ex(Tcl_Interp* interp, const char* name1, const char* name2, Tcl_Obj* newValuePtr, int flags);
Tcl_Obj *Tcl_GetVar2Ex(Tcl_Interp* interp, const char* name1, const char* name2, int flags);
int Tcl_UnsetVar2(Tcl_Interp* interp, const char* name1, const char* name2, int flags);
const Tcl_ObjType *Tcl_GetObjType(const char* typeName);

Tcl_Obj *Tcl_NewStringObj(const char* bytes, int length);
Tcl_Obj *Tcl_NewUnicodeObj(const Tcl_UniChar* unicode, int numChars);
Tcl_Obj *Tcl_NewLongObj(long longValue);
Tcl_Obj *Tcl_NewBooleanObj(int boolValue);
Tcl_Obj *Tcl_NewDoubleObj(double doubleValue);

void Tcl_IncrRefCount(Tcl_Obj* objPtr);
void Tcl_DecrRefCount(Tcl_Obj* objPtr);

int Tcl_GetBoolean(Tcl_Interp* interp, const char* src, int* boolPtr);
char *Tcl_GetString(Tcl_Obj* objPtr);
char *Tcl_GetStringFromObj(Tcl_Obj* objPtr, int* lengthPtr);

Tcl_UniChar *Tcl_GetUnicode(Tcl_Obj* objPtr);
int Tcl_GetCharLength(Tcl_Obj* objPtr);

Tcl_Obj *Tcl_NewListObj(int objc, Tcl_Obj* const objv[]);
int Tcl_ListObjLength(Tcl_Interp* interp, Tcl_Obj* listPtr, int* intPtr);
int Tcl_ListObjIndex(Tcl_Interp* interp, Tcl_Obj* listPtr, int index, Tcl_Obj** objPtrPtr);
int Tcl_SplitList(Tcl_Interp* interp, char* list, int* argcPtr, const char*** argvPtr);

int Tcl_Eval(Tcl_Interp* interp, const char* script);
int Tcl_EvalFile(Tcl_Interp* interp, const char* filename);
int Tcl_EvalObjv(Tcl_Interp* interp, int objc, Tcl_Obj** objv, int flags);
Tcl_Obj *Tcl_GetObjResult(Tcl_Interp* interp);
const char *Tcl_GetStringResult(Tcl_Interp* interp);
void Tcl_SetObjResult(Tcl_Interp* interp, Tcl_Obj* objPtr);

typedef void* ClientData;
typedef int Tcl_CmdProc(
        ClientData clientData,
        Tcl_Interp *interp,
        int argc,
        const char *argv[]);
typedef void Tcl_CmdDeleteProc(
        ClientData clientData);
Tcl_Command Tcl_CreateCommand(Tcl_Interp* interp, const char* cmdName, Tcl_CmdProc proc, ClientData clientData, Tcl_CmdDeleteProc deleteProc);
int Tcl_DeleteCommand(Tcl_Interp* interp, const char* cmdName);

Tcl_ThreadId Tcl_GetCurrentThread();
int Tcl_DoOneEvent(int flags);

int Tk_GetNumMainWindows();
""")

tklib = tkffi.verify("""
#include <tcl.h>
#include <tk.h>

char *get_tk_version() { return TK_VERSION; }
char *get_tcl_version() { return TCL_VERSION; }
""",
include_dirs=['/usr/include/tcl'],
libraries=['tcl', 'tk'],
)
