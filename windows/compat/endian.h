/* This build targets Windows x86_64, which is little-endian. */
#pragma once
#define __LITTLE_ENDIAN 1234
#define __BIG_ENDIAN 4321
#define __BYTE_ORDER __LITTLE_ENDIAN
