#ifndef _cameraspecific_features_h_
#define _cameraspecific_features_h_

/*
 * EOS 2000D / Rebel T7 feature policy
 *
 * During bring-up this file is an explicit allowlist. Do NOT include
 * all_features.h.
 *
 * Before enabling any FEATURE_* macro:
 *   1. add/update docs/2000D-130/feature-matrix.json;
 *   2. attach supporting evidence;
 *   3. make sure the feature's dependencies have reached the required
 *      QEMU/hardware validation stage.
 *
 * CI enforces these rules with tools/eos2000d/feature_matrix.py.
 *
 * No Magic Lantern user features are enabled yet.
 */

#endif
