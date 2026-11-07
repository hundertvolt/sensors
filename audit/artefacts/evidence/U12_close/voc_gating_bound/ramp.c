/* Adversarial input: a linear fall across the whole valid raw range over D days, then the floor; max gating duration. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include SRC
int main(int argc, char **argv) {
    double days = atof(argv[1]); VocAlgorithmParams p; int32_t idx; long n, total = (long)(days * 86400.0);
    double maxd = 0, at = 0; long hi = 0;
    VocAlgorithm_init(&p);
    for (n = 0; n < 2 * 3600; n++) VocAlgorithm_process(&p, 52767, &idx);
    for (n = 0; n < total + 10 * 86400L; n++) {
        long s = n < total ? 52767 - (long)((52767.0 - 20001.0) * n / total) : 20001;
        VocAlgorithm_process(&p, (int32_t)s, &idx);
        double d = p.m_Mean_Variance_Estimator___Gating_Duration_Minutes / 65536.0;
        if (idx >= 497) hi++;
        if (d > maxd) { maxd = d; at = n / 86400.0; }
    }
    printf("ramp %6.2f days: max duration %8.2f min at day %6.2f; samples at index>=497: %ld (%.2f days)\n", days, maxd, at, hi, hi / 86400.0);
    return 0;
}
