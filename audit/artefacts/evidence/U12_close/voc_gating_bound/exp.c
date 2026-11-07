/* Experiment: does the gating duration grow without bound under a worst-case input, and what does C do at int32 overflow? */
#include <stdio.h>
#include <stdint.h>
#include SRC
#define DUR(p) ((p).m_Mean_Variance_Estimator___Gating_Duration_Minutes)
int main(int argc, char **argv) {
    VocAlgorithmParams p; int32_t idx; long n; long days = 400; double maxd = 0; long at = 0;
    VocAlgorithm_init(&p);
    for (n = 0; n < 2 * 3600; n++) VocAlgorithm_process(&p, 30000, &idx);            /* 2 h clean air */
    for (n = 0; n < days * 86400L; n++) {                                              /* then the worst input the chip can give */
        VocAlgorithm_process(&p, HIGH, &idx);
        double d = DUR(p) / 65536.0; if (d > maxd) { maxd = d; at = n; }
        if (n % (86400L * 5) == 0 || n == 3600 || n == 3*3600 || n == 6*3600 || n == 12*3600) printf("day %4ld index %3d duration %.1f min\n", n / 86400L, (int)idx, d);
    }
    printf("max duration %.2f min at day %.2f\n", maxd, at / 86400.0);
    /* Overflow probe: start just below int32 max with the index held high and see what C does. */
    VocAlgorithm_init(&p);
    for (n = 0; n < 2 * 3600; n++) VocAlgorithm_process(&p, 30000, &idx);
    DUR(p) = 0x7FFFFFFF - 2000;
    for (n = 0; n < 5; n++) { VocAlgorithm_process(&p, HIGH, &idx); printf("probe %ld: index %d duration raw %ld\n", n, (int)idx, (long)DUR(p)); }
    return 0;
}
