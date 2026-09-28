#ifndef _cameraspecific_internals_h_
#define _cameraspecific_internals_h_

/*
 * Canon EOS 2000D / 1500D / Rebel T7
 * Target firmware: 1.3.0
 *
 * Phase 1 rule: only enable properties that are independent of firmware
 * addresses/structure offsets. Do not select task layouts merely to make
 * the target compile.
 */

/* The EOS 2000D/T7 is a DIGIC IV+ body. */
#define CONFIG_DIGIC_IV

/* Physical camera capabilities. */
#define CONFIG_LIVEVIEW
#define CONFIG_MOVIE
#define CONFIG_4_3_SCREEN

/*
 * Deliberately NOT enabled yet:
 *
 * CONFIG_PROP_REQUEST_CHANGE
 *   Persistent Canon properties can affect NVRAM and are inappropriate
 *   during a new port.
 *
 * CONFIG_NEW_DRYOS_TASK_HOOKS
 *   The historical 2000D.110 port used this, but firmware 1.3.0 still
 *   needs direct confirmation.
 *
 * CONFIG_TASK_STRUCT_V*
 * CONFIG_TASK_ATTR_STRUCT_V*
 * CONFIG_MALLOC_STRUCT_V*
 *   These are firmware/DryOS layout decisions. ML2000D-006 requires
 *   evidence from the exact 1.3.0 ROM before selecting them.
 */

#endif
