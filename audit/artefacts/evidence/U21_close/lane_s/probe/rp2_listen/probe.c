/* Scratch probe (lane S): where modlwip's close() stores land for a listening pcb on rp2. Each array's size is a fact read with nm. */
#include <stddef.h>
#include "lwip/tcp.h"
#include "lwip/priv/memp_priv.h"
#include "lwip/priv/tcp_priv.h"
char probe_sizeof_tcp_pcb_listen[sizeof(struct tcp_pcb_listen)];
char probe_sizeof_tcp_pcb[sizeof(struct tcp_pcb)];
char probe_offsetof_recv[offsetof(struct tcp_pcb, recv)];
char probe_offsetof_errf[offsetof(struct tcp_pcb, errf)];
char probe_memp_size_plus1[MEMP_SIZE + 1];
char probe_memp_align_size_listen[MEMP_ALIGN_SIZE(sizeof(struct tcp_pcb_listen))];
char probe_num_listen[MEMP_NUM_TCP_PCB_LISTEN];
char probe_mem_alignment[MEM_ALIGNMENT];
char probe_memp_mem_malloc_plus1[MEMP_MEM_MALLOC + 1];
char probe_memp_overflow_check_plus1[MEMP_OVERFLOW_CHECK + 1];
char probe_sizeof_ptr[sizeof(void *)];
char probe_listen_off_remote_ip_plus1[offsetof(struct tcp_pcb_listen, remote_ip) + 1];
char probe_listen_off_netif_idx_plus1[offsetof(struct tcp_pcb_listen, netif_idx) + 1];
char probe_listen_off_so_options_plus1[offsetof(struct tcp_pcb_listen, so_options) + 1];
char probe_listen_off_ttl_plus1[offsetof(struct tcp_pcb_listen, ttl) + 1];
char probe_listen_off_next_plus1[offsetof(struct tcp_pcb_listen, next) + 1];
char probe_sizeof_ip_addr[sizeof(ip_addr_t)];
char probe_sizeof_tcp_seg[sizeof(struct tcp_seg)];
