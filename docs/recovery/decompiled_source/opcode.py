# Source Generated with Decompyle++
# File: opcode.pyc (Python 3.12)

__doc__ = '\nopcode module - potentially shared between dis and other modules which\noperate on bytecodes (e.g. peephole optimizers).\n'
__all__ = [
    'cmp_op',
    'hasarg',
    'hasconst',
    'hasname',
    'hasjrel',
    'hasjabs',
    'haslocal',
    'hascompare',
    'hasfree',
    'hasexc',
    'opname',
    'opmap',
    'HAVE_ARGUMENT',
    'EXTENDED_ARG']
from _opcode import stack_effect
__all__.append('stack_effect')
cmp_op = ('<', '<=', '==', '!=', '>', '>=')
hasarg = []
hasconst = []
hasname = []
hasjrel = []
hasjabs = []
haslocal = []
hascompare = []
hasfree = []
hasexc = []
ENABLE_SPECIALIZATION = True

def is_pseudo(op):
    if op >= MIN_PSEUDO_OPCODE:
        op >= MIN_PSEUDO_OPCODE
    return op <= MAX_PSEUDO_OPCODE

oplists = [
    hasarg,
    hasconst,
    hasname,
    hasjrel,
    hasjabs,
    haslocal,
    hascompare,
    hasfree,
    hasexc]
opmap = { }
_pseudo_ops = { }

def def_op(name, op):
    opmap[name] = op


def name_op(name, op):
    def_op(name, op)
    hasname.append(op)


def jrel_op(name, op):
    def_op(name, op)
    hasjrel.append(op)


def jabs_op(name, op):
    def_op(name, op)
    hasjabs.append(op)


def pseudo_op(name, op, real_ops):
    def_op(name, op)
    _pseudo_ops[name] = real_ops
# WARNING: Decompyle incomplete

def_op('CACHE', 0)
def_op('POP_TOP', 1)
def_op('PUSH_NULL', 2)
def_op('INTERPRETER_EXIT', 3)
def_op('END_FOR', 4)
def_op('END_SEND', 5)
def_op('NOP', 9)
def_op('UNARY_NEGATIVE', 11)
def_op('UNARY_NOT', 12)
def_op('UNARY_INVERT', 15)
def_op('RESERVED', 17)
def_op('BINARY_SUBSCR', 25)
def_op('BINARY_SLICE', 26)
def_op('STORE_SLICE', 27)
def_op('GET_LEN', 30)
def_op('MATCH_MAPPING', 31)
def_op('MATCH_SEQUENCE', 32)
def_op('MATCH_KEYS', 33)
def_op('PUSH_EXC_INFO', 35)
def_op('CHECK_EXC_MATCH', 36)
def_op('CHECK_EG_MATCH', 37)
def_op('WITH_EXCEPT_START', 49)
def_op('GET_AITER', 50)
def_op('GET_ANEXT', 51)
def_op('BEFORE_ASYNC_WITH', 52)
def_op('BEFORE_WITH', 53)
def_op('END_ASYNC_FOR', 54)
def_op('CLEANUP_THROW', 55)
def_op('STORE_SUBSCR', 60)
def_op('DELETE_SUBSCR', 61)
def_op('GET_ITER', 68)
def_op('GET_YIELD_FROM_ITER', 69)
def_op('LOAD_BUILD_CLASS', 71)
def_op('LOAD_ASSERTION_ERROR', 74)
def_op('RETURN_GENERATOR', 75)
def_op('RETURN_VALUE', 83)
def_op('SETUP_ANNOTATIONS', 85)
def_op('LOAD_LOCALS', 87)
def_op('POP_EXCEPT', 89)
HAVE_ARGUMENT = 90
name_op('STORE_NAME', 90)
name_op('DELETE_NAME', 91)
def_op('UNPACK_SEQUENCE', 92)
jrel_op('FOR_ITER', 93)
def_op('UNPACK_EX', 94)
name_op('STORE_ATTR', 95)
name_op('DELETE_ATTR', 96)
name_op('STORE_GLOBAL', 97)
name_op('DELETE_GLOBAL', 98)
def_op('SWAP', 99)
def_op('LOAD_CONST', 100)
hasconst.append(100)
name_op('LOAD_NAME', 101)
def_op('BUILD_TUPLE', 102)
def_op('BUILD_LIST', 103)
def_op('BUILD_SET', 104)
def_op('BUILD_MAP', 105)
name_op('LOAD_ATTR', 106)
def_op('COMPARE_OP', 107)
hascompare.append(107)
name_op('IMPORT_NAME', 108)
name_op('IMPORT_FROM', 109)
jrel_op('JUMP_FORWARD', 110)
jrel_op('POP_JUMP_IF_FALSE', 114)
jrel_op('POP_JUMP_IF_TRUE', 115)
name_op('LOAD_GLOBAL', 116)
def_op('IS_OP', 117)
def_op('CONTAINS_OP', 118)
def_op('RERAISE', 119)
def_op('COPY', 120)
def_op('RETURN_CONST', 121)
hasconst.append(121)
def_op('BINARY_OP', 122)
jrel_op('SEND', 123)
def_op('LOAD_FAST', 124)
haslocal.append(124)
def_op('STORE_FAST', 125)
haslocal.append(125)
def_op('DELETE_FAST', 126)
haslocal.append(126)
def_op('LOAD_FAST_CHECK', 127)
haslocal.append(127)
jrel_op('POP_JUMP_IF_NOT_NONE', 128)
jrel_op('POP_JUMP_IF_NONE', 129)
def_op('RAISE_VARARGS', 130)
def_op('GET_AWAITABLE', 131)
def_op('MAKE_FUNCTION', 132)
def_op('BUILD_SLICE', 133)
jrel_op('JUMP_BACKWARD_NO_INTERRUPT', 134)
def_op('MAKE_CELL', 135)
hasfree.append(135)
def_op('LOAD_CLOSURE', 136)
hasfree.append(136)
def_op('LOAD_DEREF', 137)
hasfree.append(137)
def_op('STORE_DEREF', 138)
hasfree.append(138)
def_op('DELETE_DEREF', 139)
hasfree.append(139)
jrel_op('JUMP_BACKWARD', 140)
name_op('LOAD_SUPER_ATTR', 141)
def_op('CALL_FUNCTION_EX', 142)
def_op('LOAD_FAST_AND_CLEAR', 143)
haslocal.append(143)
def_op('EXTENDED_ARG', 144)
EXTENDED_ARG = 144
def_op('LIST_APPEND', 145)
def_op('SET_ADD', 146)
def_op('MAP_ADD', 147)
hasfree.append(148)
def_op('COPY_FREE_VARS', 149)
def_op('YIELD_VALUE', 150)
def_op('RESUME', 151)
def_op('MATCH_CLASS', 152)
def_op('FORMAT_VALUE', 155)
def_op('BUILD_CONST_KEY_MAP', 156)
def_op('BUILD_STRING', 157)
def_op('LIST_EXTEND', 162)
def_op('SET_UPDATE', 163)
def_op('DICT_MERGE', 164)
def_op('DICT_UPDATE', 165)
def_op('CALL', 171)
def_op('KW_NAMES', 172)
hasconst.append(172)
def_op('CALL_INTRINSIC_1', 173)
def_op('CALL_INTRINSIC_2', 174)
name_op('LOAD_FROM_DICT_OR_GLOBALS', 175)
def_op('LOAD_FROM_DICT_OR_DEREF', 176)
hasfree.append(176)
MIN_INSTRUMENTED_OPCODE = 237
def_op('INSTRUMENTED_LOAD_SUPER_ATTR', 237)
def_op('INSTRUMENTED_POP_JUMP_IF_NONE', 238)
def_op('INSTRUMENTED_POP_JUMP_IF_NOT_NONE', 239)
def_op('INSTRUMENTED_RESUME', 240)
def_op('INSTRUMENTED_CALL', 241)
def_op('INSTRUMENTED_RETURN_VALUE', 242)
def_op('INSTRUMENTED_YIELD_VALUE', 243)
def_op('INSTRUMENTED_CALL_FUNCTION_EX', 244)
def_op('INSTRUMENTED_JUMP_FORWARD', 245)
def_op('INSTRUMENTED_JUMP_BACKWARD', 246)
def_op('INSTRUMENTED_RETURN_CONST', 247)
def_op('INSTRUMENTED_FOR_ITER', 248)
def_op('INSTRUMENTED_POP_JUMP_IF_FALSE', 249)
def_op('INSTRUMENTED_POP_JUMP_IF_TRUE', 250)
def_op('INSTRUMENTED_END_FOR', 251)
def_op('INSTRUMENTED_END_SEND', 252)
def_op('INSTRUMENTED_INSTRUCTION', 253)
def_op('INSTRUMENTED_LINE', 254)
# WARNING: Decompyle incomplete
