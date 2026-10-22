! Magical Drop III Toretate Zoukangou (Saturn, T-1313G) -- Paddle Edition
! Shuttle Mouse, Arcade Racer, 3D Control Pad / Mission Stick (analog) and JP3 spinner
! support. SH-2 big endian, assembled per chunk by tools/build.py (gas, no linker).
!
! Rules for this file:
!  * '!@chunk name' starts a chunk. Chunks are placed anywhere in free space (4-aligned).
!  * Global labels may be used across chunks only as absolute values in literal pools
!    (mov.l .Llit,rN / jsr @rN). Branches (bra/bsr/bt/bf) stay inside a chunk.
!  * .L labels are chunk-local.
!  * No PC-relative loads (mov.l/mov.w @(disp,PC), mova) in delay slots.

	.equ	SGL_PERPTR,	0x06050b48	! SGL: pointer to Smpc_Peripheral[] (24-byte entries)
	.equ	PERIDX,		0x0607b868	! game: peripheral slot per player (long[2])
	.equ	PRESS,		0x060b3d64	! game: pressed words p1,p2 (active high)
	.equ	RELEASE,	0x060b3d68	! game: released words
	.equ	HELD,		0x060b3d6c	! game: held words
	.equ	NCOLS,		0x0605a474	! game: columns in the field (7)
	.equ	NROWS,		0x0605a478	! game: rows (12; the array holds 2*rows)
	.equ	ORIG_INPUT,	0x0600e208	! game: per-player tick buttons (pressed + d-pad repeat)

	! player struct (r4 of 0x6010e68)
	.equ	P_IDX,		0x000
	.equ	P_CPU,		0x004
	.equ	P_COL,		0x018
	.equ	P_HCOL,		0x01c	! colour held (byte, 36 = none)
	.equ	P_HELDN,	0x020	! balloons held
	.equ	P_FIELD,	0x337c	! field bytes, row-major, ncols wide, 36 = empty
	.equ	P_CATCH,	0x358
	.equ	P_THROW,	0x35a
	.equ	P_PULL,		0x35c
	.equ	P_LEFT,		0x362
	.equ	P_RIGHT,	0x364

	! SGL / game button bits (active high after inversion)
	.equ	B_RIGHT,	0x8000
	.equ	B_LEFT,		0x4000
	.equ	B_DOWN,		0x2000
	.equ	B_UP,		0x1000
	.equ	B_START,	0x0800
	.equ	B_A,		0x0400
	.equ	B_C,		0x0200
	.equ	B_B,		0x0100
	.equ	B_R,		0x0080

	! per-player state (32 bytes); byte fields < 16, word fields < 32
	.equ	S_TYPE,	0	! 0 none, 1 digital, 2 mouse, 3 jp3, 4 wheel, 5 analog
	.equ	S_ID,	1	! last SGL id
	.equ	S_LATCH,2	! jp3 latched
	.equ	S_PH,	3	! jp3 last phase 0..3
	.equ	S_AXIS,	4	! wheel / stick X (0..255)
	.equ	S_ENG,	5	! analog stick engaged
	.equ	S_IDLE,	6	! idle ticks (relative)
	.equ	S_LDIR,	7	! jp3 last direction (+1/-1)
	.equ	S_LAXIS,8	! last axis value (wheel menu taps)
	.equ	S_MFLG,	9	! menu flags: bit0 mouse has a Y axis, bit1 B withheld, bit2 tap while B held
	.equ	S_LX,	10	! last SGL mouse x (word)
	.equ	S_LY,	12	! last SGL mouse y
	.equ	S_ACC,	14	! relative counts waiting for the paddle tick
	.equ	S_POS,	16	! paddle position, 128 units per column; 0xFFFF = unsynced
	.equ	S_MX,	18	! menu accumulators
	.equ	S_MY,	20
	.equ	S_MBP,	22	! mouse buttons pressed since last tick (remapped bits)
	.equ	S_STAMP,24	! g_count at the last paddle tick (long)
	.equ	S_YACC,	28	! mouse |dy| seen since the device appeared (word, saturating)
	.equ	S_SIZE,	32

	! tuning block offsets (after the 4-byte "SDCF" tag)
	.equ	T_MSTEP,	0	! mouse counts per menu tap
	.equ	T_WSTEP,	1	! wheel units per menu tap
	.equ	T_JSTEP,	2	! jp3 edges per menu tap
	.equ	T_HREL,		3	! relative hysteresis (units past a column edge)
	.equ	T_SETTLE,	4	! idle ticks before re-centring in the column
	.equ	T_MSPEED,	5	! mouse units per count (1,2,4,8 = x0.25..x2)
	.equ	T_JUNITS,	6	! units per jp3 edge
	.equ	T_HABS,		7	! absolute hysteresis
	.equ	T_WLO,		8	! wheel range
	.equ	T_WHI,		9
	.equ	T_ARANGE,	10	! analog stick +- range across the field
	.equ	T_ADEAD,	11	! analog engage threshold
	.equ	T_INPLAY,	12	! reads since the last tick that still count as "in play"
	.equ	T_FLAGS,	13	! bit0 glide, bit1 magnet, bit2 X = pull-down, bit3 pulse target column,
				! bit4 pure paddle (never use mouse Y)
	.equ	T_YDET,		14	! mouse |dy| counts before menus also use the Y axis

!@chunk data
	.align	2
	.ascii	"SDCF"
tune:
	.byte	20		! T_MSTEP
	.byte	16		! T_WSTEP
	.byte	2		! T_JSTEP
	.byte	8		! T_HREL
	.byte	8		! T_SETTLE
	.byte	4		! T_MSPEED (x1)
	.byte	32		! T_JUNITS (4 edges per column)
	.byte	16		! T_HABS
	.byte	0x10		! T_WLO
	.byte	0xF0		! T_WHI
	.byte	0x60		! T_ARANGE
	.byte	0x28		! T_ADEAD
	.byte	3		! T_INPLAY
	.byte	29		! T_FLAGS (glide, pulse, X pull-down, pure paddle on; magnet off)
	.byte	64		! T_YDET
	.byte	0
g_count:
	.long	0
pstate:
	.fill	S_SIZE*2,1,0
pulse_phase:
	.byte	0		! 0..47, advanced once per PadRead
pulse_dirty:
	.byte	0		! the shared SPRITE struct still carries our gouraud bit
pulse_tab:			! gouraud ramp index per 4-frame step (16 = unchanged)
	.byte	12,14,16,18,20,22,24,22,20,18,16,14

!@chunk padread
! Replacement for the game's PadRead (0x06020998): fills held/pressed/released for both
! players from Smpc_Peripheral, turning mouse/wheel/spinner motion into paddle counts
! (in play) or single d-pad taps (menus).
pad_read:
	mov.l	r8,@-r15
	mov.l	r9,@-r15
	mov.l	r10,@-r15
	mov.l	r11,@-r15
	mov.l	r12,@-r15
	mov.l	r13,@-r15
	mov.l	r14,@-r15
	sts.l	pr,@-r15
	mov.l	.Lgcount,r1
	mov.l	@r1,r0
	add	#1,r0
	mov.l	r0,@r1
	mov.l	.Lphase,r1
	mov.b	@r1,r0
	add	#1,r0
	cmp/eq	#48,r0
	bf	.Lph
	mov	#0,r0
.Lph:	mov.b	r0,@r1
	mov	#0,r8
.Lploop:
	mov.l	.Lpstate,r9
	mov	r8,r0
	shll2	r0
	shll2	r0
	shll	r0
	add	r0,r9			! r9 = state
	mov.l	.Lperidx,r1
	mov	r8,r0
	shll2	r0
	mov.l	@(r0,r1),r2		! slot
	mov	r2,r0
	shll	r0
	add	r2,r0
	shll2	r0
	shll	r0			! slot*24
	mov.l	.Lsglptr,r1
	mov.l	@r1,r10
	add	r0,r10			! r10 = Smpc_Peripheral entry
	mov.w	@(2,r10),r0
	not	r0,r11
	extu.w	r11,r11			! held
	mov.w	@(4,r10),r0
	not	r0,r12
	extu.w	r12,r12			! pressed
	mov.w	@(6,r10),r0
	not	r0,r13
	extu.w	r13,r13			! released
	mov.b	@r10,r0
	mov	r0,r4			! id (sign extended)
	mov.b	@(S_ID,r9),r0
	cmp/eq	r0,r4
	bt	.Lsame
	mov	r4,r0
	mov.b	r0,@(S_ID,r9)
	mov	#0,r0
	mov.b	r0,@(S_TYPE,r9)
	mov.b	r0,@(S_LATCH,r9)
	mov.b	r0,@(S_ENG,r9)
	mov.w	r0,@(S_ACC,r9)
	mov.w	r0,@(S_MX,r9)
	mov.w	r0,@(S_MY,r9)
	mov.w	r0,@(S_MBP,r9)
	mov.b	r0,@(S_MFLG,r9)
	mov.w	r0,@(S_YACC,r9)
	mov	#-1,r0
	mov.w	r0,@(S_POS,r9)
	mov.w	@(8,r10),r0
	mov.w	r0,@(S_LX,r9)
	mov.w	@(10,r10),r0
	mov.w	r0,@(S_LY,r9)
	mov.b	@(8,r10),r0
	mov.b	r0,@(S_LAXIS,r9)
.Lsame:
	! r14 = 1 if a paddle tick ran within the last T_INPLAY reads
	mov.l	.Lgcount,r1
	mov.l	@r1,r2
	mov.l	@(S_STAMP,r9),r1
	sub	r1,r2
	mov.l	.Ltune,r1
	mov.b	@(T_INPLAY,r1),r0
	extu.b	r0,r0
	mov	#0,r14
	cmp/hs	r0,r2
	bt	.Lnotplay
	mov	#1,r14
	mov	#0,r0
	mov.w	r0,@(S_MX,r9)		! no queued menu taps while playing
	mov.w	r0,@(S_MY,r9)
.Lnotplay:
	mov	r4,r0
	cmp/eq	#-29,r0			! 0xE3 Shuttle Mouse
	bt	.Lmouse_j
	cmp/eq	#0x13,r0		! Arcade Racer
	bt	.Lwheel_j
	cmp/eq	#0x16,r0		! 3D Control Pad (analog mode)
	bt	.Lanalog_j
	cmp/eq	#0x15,r0		! Mission Stick (analog)
	bt	.Lanalog_j
	cmp/eq	#0x02,r0		! digital pad (JP3 detection)
	bt	.Ldigital_j
	mov	#0,r0
	bra	.Lstore
	mov.b	r0,@(S_TYPE,r9)
.Lmouse_j:
	mov.l	.Lmouse_a,r0
	jmp	@r0
	nop
.Lwheel_j:
	mov.l	.Lwheel_a,r0
	jmp	@r0
	nop
.Lanalog_j:
	mov.l	.Lanalog_a,r0
	jmp	@r0
	nop
.Ldigital_j:
	mov.l	.Ldigital_a,r0
	jmp	@r0
	nop

pad_read_store:
.Lstore:
	! option: in play X becomes pull-down (sent as L, like C on the Neo Geo)
	tst	r14,r14
	bt	.Lsx
	mov.l	.Ltune,r1
	mov.b	@(T_FLAGS,r1),r0
	tst	#4,r0
	bt	.Lsx
	mov	r11,r4
	bsr	.Lxpull
	nop
	mov	r0,r11
	mov	r12,r4
	bsr	.Lxpull
	nop
	mov	r0,r12
	mov	r13,r4
	bsr	.Lxpull
	nop
	mov	r0,r13
.Lsx:	mov	r8,r0
	add	r0,r0
	mov.l	.Lheld,r1
	mov.w	r11,@(r0,r1)
	mov.l	.Lpress,r1
	mov.w	r12,@(r0,r1)
	mov.l	.Lrelease,r1
	mov.w	r13,@(r0,r1)
	add	#1,r8
	mov	#2,r0
	cmp/ge	r0,r8
	bt	.Ldone
	bra	.Lploop
	nop
.Ldone:
	lds.l	@r15+,pr
	mov.l	@r15+,r14
	mov.l	@r15+,r13
	mov.l	@r15+,r12
	mov.l	@r15+,r11
	mov.l	@r15+,r10
	mov.l	@r15+,r9
	rts
	mov.l	@r15+,r8

! X (0x40) -> L (0x08): r4 in, r0 out
.Lxpull:
	mov	r4,r0
	tst	#0x40,r0
	bt	.Lxp1
	xor	#0x40,r0
	or	#0x08,r0
.Lxp1:	rts
	nop

	.align	2
.Lgcount:	.long	g_count
.Lphase:	.long	pulse_phase
.Lpstate:	.long	pstate
.Ltune:		.long	tune
.Lperidx:	.long	PERIDX
.Lsglptr:	.long	SGL_PERPTR
.Lheld:		.long	HELD
.Lpress:	.long	PRESS
.Lrelease:	.long	RELEASE
.Lmouse_a:	.long	pr_mouse
.Lwheel_a:	.long	pr_wheel
.Lanalog_a:	.long	pr_analog
.Ldigital_a:	.long	pr_digital

!@chunk prmouse
pr_mouse:
	mov	#2,r0
	mov.b	r0,@(S_TYPE,r9)
	mov.w	@(8,r10),r0		! x
	mov	r0,r5
	mov.w	@(S_LX,r9),r0
	sub	r0,r5
	exts.w	r5,r5			! dx
	mov.w	@(8,r10),r0
	mov.w	r0,@(S_LX,r9)
	mov.w	@(10,r10),r0		! y (positive = down)
	mov	r0,r6
	mov.w	@(S_LY,r9),r0
	sub	r0,r6
	exts.w	r6,r6			! dy
	mov.w	@(10,r10),r0
	mov.w	r0,@(S_LY,r9)
	mov.l	.Lydet_m,r0
	jsr	@r0			! notice a real Y axis (full mouse / trackball)
	nop
	! L+R chord = START
	mov.w	.Lw0600,r1
	mov	r11,r0
	and	r1,r0
	cmp/eq	r1,r0
	bf	.Lnochord
	mov.w	.Lw0800,r2
	or	r2,r11
	tst	r1,r12
	bt	.Lnochord
	or	r2,r12
.Lnochord:
	mov	r11,r4
	bsr	.Lremap
	nop
	mov	r0,r11
	mov	r12,r4
	bsr	.Lremap
	nop
	mov	r0,r12
	mov	r13,r4
	bsr	.Lremap
	nop
	mov	r0,r13
	mov.w	@(S_MBP,r9),r0
	or	r12,r0
	mov.w	r0,@(S_MBP,r9)
	tst	r14,r14
	bt	.Lmmenu
	! in play: queue counts for the paddle tick (saturating)
	mov.w	@(S_ACC,r9),r0
	add	r5,r0
	mov.w	.Lw7000,r1
	cmp/gt	r1,r0
	bf	.Lm1
	mov	r1,r0
.Lm1:	neg	r1,r1
	cmp/ge	r1,r0
	bt	.Lm2
	mov	r1,r0
.Lm2:	bra	.Lmret
	mov.w	r0,@(S_ACC,r9)
.Lmmenu:
	mov.l	.Ltune_m,r1
	mov.b	@(T_MSTEP,r1),r0
	extu.b	r0,r7
	mov.l	.Lmenutap_m,r0
	jsr	@r0
	nop
.Lmret:
	mov.l	.Lstore_m,r0
	jmp	@r0
	nop

! mouse buttons: left -> A, right -> B, middle -> R trigger, START kept. r4 in, r0 out
.Lremap:
	mov.w	.Lw0800,r0
	and	r4,r0
	mov.w	.Lw0400,r1
	tst	r1,r4
	bt	.Lr1
	or	r1,r0
.Lr1:	mov.w	.Lw0200,r1
	tst	r1,r4
	bt	.Lr2
	mov.w	.Lw0100,r1
	or	r1,r0
.Lr2:	mov.w	.Lw0100,r1
	tst	r1,r4
	bt	.Lr3
	or	#0x80,r0
.Lr3:	rts
	nop

	.align	1
.Lw0100: .word	0x0100
.Lw0200: .word	0x0200
.Lw0400: .word	0x0400
.Lw0600: .word	0x0600
.Lw0800: .word	0x0800
.Lw7000: .word	0x7000
	.align	2
.Ltune_m:	.long	tune
.Lmenutap_m:	.long	menu_tap
.Lydet_m:	.long	y_detect
.Lstore_m:	.long	pad_read_store

!@chunk prdev
! Device branches of pad_read. Entered by jmp with pad_read's registers live
! (r8 player, r9 state, r10 entry, r11/r12/r13 held/pressed/released, r14 in play);
! each one jumps back to pad_read's store step (pr_store).
pr_wheel:
	mov	#4,r0
	mov.b	r0,@(S_TYPE,r9)
	mov.b	@(8,r10),r0
	extu.b	r0,r4
	mov	r4,r0
	mov.b	r0,@(S_AXIS,r9)
	mov.b	@(S_LAXIS,r9),r0
	extu.b	r0,r5
	mov	r4,r0
	mov.b	r0,@(S_LAXIS,r9)
	sub	r5,r4			! wheel delta
	! the Arcade Racer reports LEFT/RIGHT from the wheel angle: never pass those on
	mov.w	.Lwc000,r1
	not	r1,r1
	and	r1,r11
	and	r1,r12
	and	r1,r13
	tst	r14,r14
	bf	.Lpw_ret
	mov	r4,r5
	mov	#0,r6
	mov.l	.Ltune2,r1
	mov.b	@(T_WSTEP,r1),r0
	extu.b	r0,r7
	mov.l	.Lmenutap_b,r0
	jsr	@r0
	nop
.Lpw_ret:
	mov.l	.Lstore_a,r0
	jmp	@r0
	nop

pr_analog:
	mov.b	@(8,r10),r0
	extu.b	r0,r4
	mov	r4,r0
	mov.b	r0,@(S_AXIS,r9)
	add	#-128,r4
	cmp/pz	r4
	bt	.Lpa1
	neg	r4,r4
.Lpa1:	mov.l	.Ltune2,r1
	mov.b	@(T_ADEAD,r1),r0
	extu.b	r0,r0
	cmp/gt	r0,r4
	bf	.Lpa2
	mov	#1,r0
	mov.b	r0,@(S_ENG,r9)
.Lpa2:	mov.w	.Lwc000,r1
	tst	r1,r11			! d-pad left/right hands control back to the d-pad
	bt	.Lpa3
	mov	#0,r0
	mov.b	r0,@(S_ENG,r9)
.Lpa3:	mov.b	@(S_ENG,r9),r0
	tst	r0,r0
	mov	#1,r0
	bt	.Lpa4
	mov	#5,r0
.Lpa4:	mov.b	r0,@(S_TYPE,r9)
	bra	pr_jp3
	nop

pr_digital:
	mov	#1,r0
	mov.b	r0,@(S_TYPE,r9)
pr_jp3:
	! two spinner wirings: d-pad LEFT/RIGHT, or Y/Z (phase A on Y, phase B on Z)
	mov	r11,r4
	shlr8	r4
	shlr2	r4
	shlr2	r4
	shlr2	r4			! r4 = held >> 14: bit0 LEFT (A), bit1 RIGHT (B)
	mov	r11,r0
	shlr2	r0
	shlr2	r0			! bit0 Z, bit1 Y
	and	#3,r0
	mov	r0,r3
	shlr	r3			! Y -> bit0
	and	#1,r0
	shll	r0			! Z -> bit1
	or	r0,r3			! r3 = Y/Z pair
	mov.b	@(S_LATCH,r9),r0	! first read with both lines of a pair: a spinner
	tst	r0,r0
	bf	.Lpd1
	mov	r4,r0
	cmp/eq	#3,r0
	bf	.Lpd0
	mov	#1,r0			! latched on the d-pad
	bra	.Lpd_lat
	nop
.Lpd0:	mov	r3,r0
	cmp/eq	#3,r0
	bf	.Lpw_ret
	mov	#2,r0			! latched on Y/Z
.Lpd_lat:
	mov.b	r0,@(S_LATCH,r9)
	mov	#2,r0			! phase of A=1,B=1
	mov.b	r0,@(S_PH,r9)
.Lpd1:	mov.b	@(S_LATCH,r9),r0
	cmp/eq	#2,r0
	bf	.Lpd_dp
	mov	r3,r4			! decode Y/Z
	mov	#0x30,r3		! and strip Y/Z
	bra	.Lpd_go
	nop
.Lpd_dp:
	mov.w	.Lwc000,r3		! strip LEFT/RIGHT
	extu.w	r3,r3
.Lpd_go:
	mov	#3,r0
	mov.b	r0,@(S_TYPE,r9)
	! phase p = A xor 3B : 00,10,11,01 -> 0,1,2,3
	mov	r4,r0
	and	#1,r0
	mov	r0,r5			! A
	mov	r4,r0
	shlr	r0
	and	#1,r0
	mov	r0,r6
	add	r0,r6
	add	r0,r6			! 3B
	xor	r6,r5			! p
	mov.b	@(S_PH,r9),r0
	extu.b	r0,r6
	mov	r5,r0
	mov.b	r0,@(S_PH,r9)
	sub	r6,r0
	and	#3,r0			! delta mod 4
	mov	#0,r5			! steps
	cmp/eq	#1,r0
	bf	.Lpd2
	mov	#1,r0
	mov	r0,r5
	bra	.Lpd4
	mov.b	r0,@(S_LDIR,r9)
.Lpd2:	cmp/eq	#3,r0
	bf	.Lpd3
	mov	#-1,r5
	mov	r5,r0
	bra	.Lpd5
	mov.b	r0,@(S_LDIR,r9)
.Lpd3:	cmp/eq	#2,r0			! both phases changed: two edges in the last direction
	bf	.Lpd5
	mov.b	@(S_LDIR,r9),r0
	mov	r0,r5
	bra	.Lpd5
	add	r5,r5
.Lpd4:
.Lpd5:	not	r3,r1			! spinner lines never reach the game
	and	r1,r11
	and	r1,r12
	and	r1,r13
	tst	r14,r14
	bt	.Lpd_menu
	mov.w	@(S_ACC,r9),r0
	add	r5,r0
	bra	.Lpw_ret
	mov.w	r0,@(S_ACC,r9)
.Lpd_menu:
	mov	#0,r6
	mov.l	.Ltune2,r1
	mov.b	@(T_JSTEP,r1),r0
	extu.b	r0,r7
	mov.l	.Lmenutap_b,r0
	jsr	@r0
	nop
	bra	.Lpw_ret
	nop
	.align	1
.Lwc000: .word	0xC000
	.align	2
.Ltune2:	.long	tune
.Lmenutap_b:	.long	menu_tap
.Lstore_a:	.long	pad_read_store

!@chunk menutap
! menu_tap: r5 = dx, r6 = dy, r7 = counts per tap; r9 = state; may OR one d-pad tap into
! r11 (held) and r12 (pressed). The larger axis wins; remainder carried; at most one tap.
menu_tap:
	mov.b	@(S_TYPE,r9),r0
	cmp/eq	#3,r0			! JP3: X only
	bt	.Lxonly
	cmp/eq	#2,r0
	bf	.Lxy
	mov.b	@(S_MFLG,r9),r0		! mouse without a Y axis seen yet: X only
	tst	#1,r0
	bf	.Lxy
.Lxonly:
	mov.l	.Lxmenu,r0
	jmp	@r0
	nop
.Lxy:
	mov.w	@(S_MX,r9),r0
	add	r0,r5
	mov.w	@(S_MY,r9),r0
	add	r0,r6
	! clamp both to +-4 steps
	mov	r7,r1
	shll2	r1
	cmp/gt	r1,r5
	bf	.Lc1
	mov	r1,r5
.Lc1:	cmp/gt	r1,r6
	bf	.Lc2
	mov	r1,r6
.Lc2:	neg	r1,r1
	cmp/ge	r1,r5
	bt	.Lc3
	mov	r1,r5
.Lc3:	cmp/ge	r1,r6
	bt	.Lc4
	mov	r1,r6
.Lc4:	mov	r5,r1			! |dx|
	cmp/pz	r1
	bt	.Lc5
	neg	r1,r1
.Lc5:	mov	r6,r2			! |dy|
	cmp/pz	r2
	bt	.Lc6
	neg	r2,r2
.Lc6:	mov	#0,r3			! tap bit
	cmp/hs	r2,r1			! |dx| >= |dy| ?
	bf	.Ly
	cmp/hs	r7,r1
	bf	.Lout
	cmp/pz	r5
	bf	.Lxl
	sub	r7,r5
	mov.w	.Lright,r3
	bra	.Lout
	nop
.Lxl:	add	r7,r5
	mov.w	.Lleft,r3
	bra	.Lout
	nop
.Ly:	cmp/hs	r7,r2
	bf	.Lout
	cmp/pz	r6
	bf	.Lyu
	sub	r7,r6
	mov.w	.Ldown,r3
	bra	.Lout
	nop
.Lyu:	add	r7,r6
	mov.w	.Lup,r3
.Lout:	or	r3,r11
	or	r3,r12
	mov	r5,r0
	mov.w	r0,@(S_MX,r9)
	mov	r6,r0
	rts
	mov.w	r0,@(S_MY,r9)
	.align	1
.Lright: .word	0x8000
.Lleft:	 .word	0x4000
.Ldown:	 .word	0x2000
.Lup:	 .word	0x1000
	.align	2
.Lxmenu: .long	x_menu

!@chunk xmenu
! Menus for paddle-only devices (spinner as Shuttle Mouse, JP3). Only X is used; it is
! turned into the tap the current screen needs:
!   vertical lists (mode/level/rule select, options, custom rules, sugoroku board menu):
!     +X = DOWN, -X = UP
!   character select: 2-row grids walk in reading order (row ends hop to the other row
!     through the game's own wrap), 1-row grids use LEFT/RIGHT
!   everything else (continue, results, title): LEFT/RIGHT
! Holding B (mouse right) or R (mouse middle) swaps vertical and horizontal, so option
! values can be changed. B is held back while it is down and delivered on release, unless
! X moved while it was held.
! Same entry as menu_tap: r5 dx, r7 counts per tap, r8 player, r9 state, r11/r12 held/pressed.
	.equ	G_STATE,	0x0608de74	! game: top-level state (5 menus, 6 play, 7 sugoroku board)
	.equ	G_MODE,		0x0605a434	! game: mode select cursor (0 story .. 4 options)
	.equ	G_DEPTH,	0x06087414	! game: menu screen depth within the mode
	.equ	G_CUR_ST,	0x06087384	! game: story character cursor (0..6 top, 7..15 bottom)
	.equ	G_CUR_VS,	0x0608738c	! game: VS character cursors, P1 then P2
x_menu:
	mov.b	@(S_MFLG,r9),r0
	mov	r0,r4			! r4 = flags
	mov.w	.Lxb,r1
	mov	#0,r3			! r3 = axis swap (modifier)
	tst	r1,r11
	bt	.Lnob
	not	r1,r2			! B down: hold it back
	and	r2,r11
	and	r2,r12
	or	#2,r0
	mov	r0,r4
	bra	.Lmod
	mov	#1,r3
.Lnob:	tst	#2,r0
	bt	.Lrt
	tst	#4,r0			! B released: deliver it unless X moved meanwhile
	bf	.Lspun
	or	r1,r11
	or	r1,r12
.Lspun:	and	#0xF9,r0
	mov	r0,r4
.Lrt:	mov	r11,r0
	tst	#0x80,r0		! R held also swaps axes
	bt	.Lmod
	mov	#1,r3
.Lmod:	mov.w	@(S_MX,r9),r0
	add	r0,r5
	mov	r7,r1			! clamp to +-4 taps
	shll2	r1
	cmp/gt	r1,r5
	bf	.Lk1
	mov	r1,r5
.Lk1:	neg	r1,r1
	cmp/ge	r1,r5
	bt	.Lk2
	mov	r1,r5
.Lk2:	mov	r5,r1
	cmp/pz	r1
	bt	.Lk3
	neg	r1,r1
.Lk3:	cmp/hs	r7,r1
	bf	.Lsave
	mov	#1,r6			! r6 = +1 / -1
	cmp/pz	r5
	bf	.Lk4
	bra	.Lk5
	sub	r7,r5
.Lk4:	add	r7,r5
	mov	#-1,r6
.Lk5:	mov	r4,r0			! a tap while B is held: B will not be sent
	tst	#2,r0
	bt	.Lscr
	or	#4,r0
	mov	r0,r4
.Lscr:	mov.l	.Lgstate,r1
	mov.l	@r1,r0
	cmp/eq	#7,r0
	bt	.Lvert
	cmp/eq	#5,r0
	bf	.Lhorz
	mov.l	.Lgdepth,r2
	mov.l	@r2,r2
	mov.l	.Lgmode,r1
	mov.l	@r1,r0
	cmp/eq	#0,r0
	bf	.Lm1
	mov	r2,r0			! story: depth 2 = 2-row grid
	cmp/eq	#2,r0
	bf	.Lvert
	mov.l	.Lcurst,r7
	bra	.Lgrid
	nop
.Lm1:	cmp/eq	#1,r0
	bf	.Lm2
	mov	r2,r0			! VS: depth 3 = 2-row grid, one cursor per player
	cmp/eq	#3,r0
	bf	.Lvert
	mov.l	.Lcurvs,r7
	mov	r8,r0
	shll2	r0
	bra	.Lgrid
	add	r0,r7
.Lm2:	cmp/eq	#2,r0			! puzzle / sugoroku: depth 2 = 1-row grid
	bt	.Lm3
	cmp/eq	#3,r0
	bf	.Lvert
.Lm3:	mov	r2,r0
	cmp/eq	#2,r0
	bt	.Lhorz
.Lvert:	tst	r3,r3
	bf	.Lh
.Lv:	cmp/pz	r6
	bt	.Ldn
	bra	.Lemit
	mov	#0x10,r1		! UP (0x1000 >> 8)
.Ldn:	bra	.Lemit
	mov	#0x20,r1		! DOWN
.Lhorz:	tst	r3,r3
	bf	.Lv
.Lh:	cmp/pz	r6
	bt	.Lrr
.Lll:	bra	.Lemit
	mov	#0x40,r1		! LEFT
.Lrr:	bra	.Lemit
	mov	#-128,r1		! RIGHT (0x80, sign-extended; masked below)
.Lgrid:	mov.l	@r7,r0
	tst	r3,r3			! modifier: hop to the other row
	bt	.Lg0
	mov	#7,r1
	cmp/ge	r1,r0
	bf	.Ldn
	bra	.Lemit
	mov	#0x10,r1		! UP
.Lg0:
	cmp/pz	r6
	bf	.Lgl
	cmp/eq	#6,r0			! end of top row -> start of bottom row
	bf	.Lg1
	mov	#15,r0
	bra	.Lrr
	mov.l	r0,@r7
.Lg1:	cmp/eq	#15,r0			! end of bottom row -> start of top row
	bf	.Lrr
	mov	#6,r0
	bra	.Lrr
	mov.l	r0,@r7
.Lgl:	cmp/eq	#7,r0			! start of bottom row -> end of top row
	bf	.Lg2
	mov	#0,r0
	bra	.Lll
	mov.l	r0,@r7
.Lg2:	cmp/eq	#0,r0			! start of top row -> end of bottom row
	bf	.Lll
	mov	#7,r0
	bra	.Lll
	mov.l	r0,@r7
.Lemit:	extu.b	r1,r1
	shll8	r1
	or	r1,r11
	or	r1,r12
.Lsave:	mov	r5,r0
	mov.w	r0,@(S_MX,r9)
	mov	#0,r0
	mov.w	r0,@(S_MY,r9)
	mov	r4,r0
	rts
	mov.b	r0,@(S_MFLG,r9)

	.align	1
.Lxb:	.word	0x0100
	.align	2
.Lgstate:	.long	G_STATE
.Lgmode:	.long	G_MODE
.Lgdepth:	.long	G_DEPTH
.Lcurst:	.long	G_CUR_ST
.Lcurvs:	.long	G_CUR_VS

!@chunk ydet
! y_detect: r6 = mouse dy this read. Once enough Y motion has been seen (T_YDET counts),
! the device is a full mouse or trackball and menus use both axes again (unless the
! pure-paddle flag is set). Uses r0-r2.
y_detect:
	mov	r6,r1
	cmp/pz	r1
	bt	.Ly1
	neg	r1,r1
.Ly1:	mov.w	@(S_YACC,r9),r0
	add	r1,r0
	mov.w	.Lysat,r1
	cmp/gt	r1,r0
	bf	.Ly2
	mov	r1,r0
.Ly2:	mov.w	r0,@(S_YACC,r9)
	mov	r0,r2
	mov.l	.Lxtune,r1
	mov.b	@(T_FLAGS,r1),r0
	tst	#16,r0
	bf	.Ly3
	mov.b	@(T_YDET,r1),r0
	extu.b	r0,r0
	cmp/hs	r0,r2
	bf	.Ly3
	mov.b	@(S_MFLG,r9),r0
	or	#1,r0
	mov.b	r0,@(S_MFLG,r9)
.Ly3:	rts
	nop
	.align	1
.Lysat:	.word	0x7000
	.align	2
.Lxtune:	.long	tune

!@chunk tick
! Wrapper for ORIG_INPUT inside the clown movement routine (0x06010e68): r4 = player
! struct. Returns the tick buttons with the paddle's single left/right step injected.
paddle_tick:
	sts.l	pr,@-r15
	mov.l	r8,@-r15
	mov.l	r9,@-r15
	mov.l	r10,@-r15
	mov.l	r11,@-r15
	mov.l	r12,@-r15
	mov	r4,r8
	mov.l	.Lorig,r0
	jsr	@r0
	nop
	mov	r0,r9			! buttons
	mov.l	@(P_CPU,r8),r0
	cmp/eq	#1,r0
	bt	.Lret_j
	mov.l	@(P_IDX,r8),r0
	mov	#2,r1
	cmp/hs	r1,r0
	bt	.Lret_j
	shll2	r0
	shll2	r0
	shll	r0
	mov.l	.Lpstate_t,r10
	add	r0,r10			! state
	mov.l	.Lgcount_t,r1
	mov.l	@r1,r0
	mov.l	r0,@(S_STAMP,r10)
	mov.b	@(S_TYPE,r10),r0
	mov	#2,r1
	cmp/hs	r1,r0
	bf	.Lret_j
	mov	r0,r12			! type
	mov.w	.Lo_left,r0
	mov.w	@(r0,r8),r1
	mov.w	.Lo_right,r0
	mov.w	@(r0,r8),r2
	or	r2,r1
	! a Y/Z spinner leaves the d-pad live: a real left/right press moves the clown
	! and the paddle re-centres on the new column
	mov.b	@(S_LATCH,r10),r0
	cmp/eq	#2,r0
	bf	.Lstrip
	tst	r1,r9
	bt	.Lstrip
	mov	#-1,r0
	mov.w	r0,@(S_POS,r10)
	bra	.Lret_j
	nop
.Lstrip:
	! strip the real left/right of this player's configuration
	not	r1,r1
	and	r1,r9
	mov.l	.Lncols,r1
	mov.l	@r1,r11
	shll8	r11
	shlr	r11			! r11 = width = ncols*128
	mov	r12,r0
	cmp/eq	#4,r0
	bt	.Labs_j
	cmp/eq	#5,r0
	bt	.Labs_j
	mov.l	.Lrel_a,r0
	jmp	@r0
	nop
.Labs_j:
	mov.l	.Labs_a,r0
	jmp	@r0
	nop
.Lret_j:
	mov.l	.Lret_a,r0
	jmp	@r0
	nop
	.align	1
.Lo_left:  .word P_LEFT
.Lo_right: .word P_RIGHT
	.align	2
.Lorig:		.long	ORIG_INPUT
.Lpstate_t:	.long	pstate
.Lgcount_t:	.long	g_count
.Lncols:	.long	NCOLS
.Lrel_a:	.long	tick_rel
.Labs_a:	.long	tick_abs
.Lret_a:	.long	tick_ret

!@chunk tickrel
! relative devices (mouse, jp3): r8 struct, r9 buttons, r10 state, r11 width, r12 type
tick_rel:
	mov.l	.Ltune_r,r6
	mov.w	@(S_ACC,r10),r0
	mov	r0,r4			! counts
	mov	#0,r0
	mov.w	r0,@(S_ACC,r10)
	mov	r12,r0
	cmp/eq	#2,r0
	bf	.Ltr_jp3
	mov.b	@(T_MSPEED,r6),r0
	bra	.Ltr_mul
	extu.b	r0,r5
.Ltr_jp3:
	mov.b	@(T_JUNITS,r6),r0
	extu.b	r0,r5
.Ltr_mul:
	muls.w	r4,r5
	sts	macl,r5			! units
	! position not synced yet (new device): start in the middle of the current column
	mov.w	@(S_POS,r10),r0
	extu.w	r0,r7
	mov.w	.Lffff,r1
	extu.w	r1,r1
	cmp/eq	r1,r7
	bf	.Ltr_s
	mov.l	@(P_COL,r8),r7
	shll8	r7
	shlr	r7
	add	#64,r7
.Ltr_s:	tst	r4,r4
	bf	.Ltr_moving
	mov.b	@(T_SETTLE,r6),r0
	extu.b	r0,r1
	mov.b	@(S_IDLE,r10),r0
	extu.b	r0,r0
	cmp/hs	r1,r0
	bt	.Ltr_settled
	add	#1,r0
	mov.b	r0,@(S_IDLE,r10)
	cmp/hs	r1,r0
	bf	.Ltr_apply
.Ltr_settled:
	mov.l	@(P_COL,r8),r7		! idle: sit in the middle of the clown's column
	shll8	r7
	shlr	r7
	add	#64,r7
	bra	.Ltr_apply
	nop
.Ltr_moving:
	mov	#0,r0
	mov.b	r0,@(S_IDLE,r10)
	! magnet: the mouse moves at half speed over a column it can catch from
	mov	r12,r0
	cmp/eq	#2,r0
	bf	.Ltr_apply
	mov	r7,r1
	shll	r1
	shlr8	r1			! r1 = pos >> 7 (column under the paddle)
	mov.l	.Lmagnet_r,r0
	jsr	@r0
	nop
	tst	r0,r0
	bt	.Ltr_apply
	shar	r5
.Ltr_apply:
	add	r5,r7
	cmp/pz	r7
	bt	.Ltr_c1
	mov	#0,r7
.Ltr_c1:
	cmp/ge	r11,r7
	bf	.Ltr_c2
	mov	r11,r7
	add	#-1,r7
.Ltr_c2:
	mov	r7,r0
	mov.w	r0,@(S_POS,r10)
	mov.b	@(T_HREL,r6),r0
	extu.b	r0,r6			! hysteresis
	mov	r12,r0
	cmp/eq	#2,r0
	bf	.Ltr_dec
	! mouse buttons through this player's catch / throw / pull-down masks
	mov.w	.Lw0580,r1
	not	r1,r1
	and	r1,r9
	mov.w	@(S_MBP,r10),r0
	mov	r0,r4
	mov	#0,r0
	mov.w	r0,@(S_MBP,r10)
	mov.w	.Lw0400r,r1
	tst	r1,r4
	bt	.Ltr_b1
	mov.w	.Lo_catch,r0
	mov.w	@(r0,r8),r1
	neg	r1,r2
	and	r2,r1
	extu.w	r1,r1
	or	r1,r9
.Ltr_b1:
	mov.w	.Lw0100r,r1
	tst	r1,r4
	bt	.Ltr_b2
	mov.w	.Lo_throw,r0
	mov.w	@(r0,r8),r1
	neg	r1,r2
	and	r2,r1
	extu.w	r1,r1
	or	r1,r9
.Ltr_b2:
	mov	r4,r0
	tst	#0x80,r0
	bt	.Ltr_dec
	mov.w	.Lo_pull,r0
	mov.w	@(r0,r8),r1
	neg	r1,r2
	and	r2,r1
	extu.w	r1,r1
	or	r1,r9
.Ltr_dec:
	mov.l	.Ldecide_a,r0
	jmp	@r0
	nop
	.align	1
.Lffff:	  .word	0xFFFF
.Lw0580:  .word	0x0580
.Lw0400r: .word	0x0400
.Lw0100r: .word	0x0100
.Lo_catch: .word P_CATCH
.Lo_throw: .word P_THROW
.Lo_pull:  .word P_PULL
	.align	2
.Ltune_r:	.long	tune
.Ldecide_a:	.long	tick_decide
.Lmagnet_r:	.long	magnet

!@chunk tickabs
! absolute devices (wheel, analog stick): position straight from the axis
tick_abs:
	mov.l	.Ltune_a,r6
	mov.b	@(S_AXIS,r10),r0
	extu.b	r0,r4
	mov	r12,r0
	cmp/eq	#4,r0
	bf	.Lta_stick
	mov.b	@(T_WLO,r6),r0
	extu.b	r0,r1			! lo
	mov.b	@(T_WHI,r6),r0
	extu.b	r0,r2
	bra	.Lta_map
	sub	r1,r2			! span
.Lta_stick:
	mov.b	@(T_ARANGE,r6),r0
	extu.b	r0,r2
	mov	#-128,r1
	extu.b	r1,r1			! 0x80
	sub	r2,r1			! lo = 0x80 - range
	add	r2,r2			! span = 2*range
.Lta_map:
	sub	r1,r4			! v = axis - lo
	cmp/pz	r4
	bt	.Lta_1
	mov	#0,r4
.Lta_1:	cmp/gt	r2,r4
	bf	.Lta_2
	mov	r2,r4
.Lta_2:	mulu.w	r4,r11
	sts	macl,r1			! v*width
	! r1 / r2 (quotient < 65536 since v <= span)
	shll16	r2
	div0u
	.rept	16
	div1	r2,r1
	.endr
	rotcl	r1
	extu.w	r1,r7			! pos
	cmp/ge	r11,r7
	bf	.Lta_3
	mov	r11,r7
	add	#-1,r7
.Lta_3:	mov	r7,r0
	mov.w	r0,@(S_POS,r10)
	mov.l	@(P_COL,r8),r1		! magnet: 4x hysteresis on a column it can catch from
	mov.l	.Lmagnet_a,r0
	jsr	@r0
	nop
	mov	r0,r1
	mov.b	@(T_HABS,r6),r0
	extu.b	r0,r6
	tst	r1,r1
	bt	.Lta_4
	shll2	r6
.Lta_4:	mov.l	.Ldecide_b,r0
	jmp	@r0
	nop
	.align	2
.Ltune_a:	.long	tune
.Ldecide_b:	.long	tick_decide
.Lmagnet_a:	.long	magnet

!@chunk tickdec
! r7 = pos, r6 = hysteresis: one column step toward the paddle per tick
tick_decide:
	mov.l	@(P_COL,r8),r1		! col
	mov	r1,r2
	shll8	r2
	shlr	r2			! left edge = col*128
	mov	r2,r3
	sub	r6,r3			! left edge - h
	cmp/ge	r3,r7
	bt	.Ltd_r
	tst	r1,r1			! never past column 0 (the game may wrap)
	bt	.Ltd_x
	mov.w	.Lo_left2,r0
	bra	.Ltd_inj
	nop
.Ltd_r:	mov	r2,r3
	add	#127,r3
	add	#1,r3
	add	r6,r3			! right edge + h
	cmp/ge	r3,r7
	bf	.Ltd_x
	mov.l	.Lncols2,r3
	mov.l	@r3,r3
	add	#-1,r3
	cmp/ge	r3,r1
	bt	.Ltd_x
	mov.w	.Lo_right2,r0
.Ltd_inj:
	mov.w	@(r0,r8),r1
	neg	r1,r2
	and	r2,r1			! lowest bit of the mask
	extu.w	r1,r1
	or	r1,r9
.Ltd_x:
tick_ret:
	mov	r9,r0
	mov.l	@r15+,r12
	mov.l	@r15+,r11
	mov.l	@r15+,r10
	mov.l	@r15+,r9
	mov.l	@r15+,r8
	lds.l	@r15+,pr
	rts
	nop
	.align	1
.Lo_left2:  .word P_LEFT
.Lo_right2: .word P_RIGHT
	.align	2
.Lncols2:	.long	NCOLS

!@chunk magnet
! magnet: r8 = player struct, r1 = column. r0 = 1 when the clown holds balloons and the
! lowest balloon of that column has the held colour. Clobbers r1-r3 only.
magnet:
	mov.l	r4,@-r15
	mov.l	r5,@-r15
	mov	#0,r4
	mov.l	.Lmg_tune,r0
	mov.b	@(T_FLAGS,r0),r0
	tst	#2,r0
	bt	.Lmg_x
	mov.l	@(P_HELDN,r8),r0
	tst	r0,r0
	bt	.Lmg_x
	mov	#P_HCOL,r0
	mov.b	@(r0,r8),r3
	extu.b	r3,r3			! held colour
	mov.w	.Lmg_fld,r5
	add	r8,r5
	add	r1,r5			! r5 = &field[0][col]
	mov.l	.Lmg_nc,r2
	mov.l	@r2,r2			! stride = ncols
	mov.l	.Lmg_nr,r1
	mov.l	@r1,r1
	add	r1,r1			! rows in the array
	mov	#-1,r4			! lowest balloon so far
.Lmg_l:	mov.b	@r5,r0
	extu.b	r0,r0
	cmp/eq	#36,r0
	bt	.Lmg_e
	mov	r0,r4
.Lmg_e:	dt	r1
	bf/s	.Lmg_l
	add	r2,r5
	cmp/eq	r3,r4
	movt	r4
.Lmg_x:	mov	r4,r0
	mov.l	@r15+,r5
	rts
	mov.l	@r15+,r4
	.align	1
.Lmg_fld: .word	P_FIELD
	.align	2
.Lmg_nc:	.long	NCOLS
.Lmg_nr:	.long	NROWS
.Lmg_tune:	.long	tune

!@chunk glide
! Clown / aim line drawn at the paddle position, clamped to one column either side of the
! real column. Called from four patched draw sites with an inline literal after the jsr:
! return address = align4(PR) + 4. r11 = player struct at every site.
!   glide_tab:    r1 = G                      (aim line, replaces table[col] = col<<20)
!   glide_add0:   r0 += G, r1 = 0             (col<<20)
!   glide_add_m8: r0 += G - (8<<16), r1 = 0   ((col*16-8)<<16)
glide_tab:
	bra	.Lg
	mov	#0,r1
glide_add0:
	bra	.Lg
	mov	#1,r1
glide_add_m8:
	mov	#2,r1
.Lg:	mov.l	r2,@-r15
	mov.l	r3,@-r15
	mov.l	r4,@-r15
	mov.l	r5,@-r15
	mov.l	r6,@-r15
	mov.l	r0,@-r15
	mov	r1,r6			! mode
	mov.l	@(P_COL,r11),r2
	mov	r2,r1
	shll2	r1
	shll2	r1			! default: col*16
	mov.l	.Lg_tune,r0
	mov.b	@(T_FLAGS,r0),r0
	tst	#1,r0
	bt	.Lg_d
	mov.l	@(P_CPU,r11),r0
	cmp/eq	#1,r0
	bt	.Lg_d
	mov.l	@(P_IDX,r11),r3
	mov	#2,r4
	cmp/hs	r4,r3
	bt	.Lg_d
	shll2	r3
	shll2	r3
	shll	r3
	mov.l	.Lg_ps,r4
	add	r3,r4			! state
	mov.b	@(S_TYPE,r4),r0
	extu.b	r0,r0
	mov	#2,r3
	cmp/hs	r3,r0
	bf	.Lg_d
	mov.w	@(S_POS,r4),r0
	extu.w	r0,r3
	mov.w	.Lg_ffff,r0
	extu.w	r0,r0
	cmp/eq	r0,r3
	bt	.Lg_d
	shlr2	r3
	shlr	r3
	add	#-8,r3			! vis = pos/8 - 8
	mov	r1,r4
	add	#-16,r4
	cmp/ge	r4,r3
	bt	.Lg_1
	mov	r4,r3
.Lg_1:	mov	r1,r4
	add	#16,r4
	cmp/gt	r4,r3
	bf	.Lg_2
	mov	r4,r3
.Lg_2:	cmp/pz	r3
	bt	.Lg_3
	mov	#0,r3
.Lg_3:	mov.l	.Lg_nc,r4
	mov.l	@r4,r4
	add	#-1,r4
	shll2	r4
	shll2	r4
	cmp/gt	r4,r3
	bf	.Lg_4
	mov	r4,r3
.Lg_4:	mov	r3,r1
.Lg_d:	shll16	r1			! G
	mov.l	@r15+,r0
	tst	r6,r6
	bt	.Lg_ret
	add	r1,r0
	mov	r6,r2
	mov	#0,r1
	mov	#2,r3
	cmp/eq	r3,r2
	bf	.Lg_ret
	mov.l	.Lg_8,r2
	sub	r2,r0
.Lg_ret:
	sts	pr,r2			! skip the inline literal
	add	#3,r2
	mov	#-4,r3
	and	r3,r2
	add	#4,r2
	lds	r2,pr
	mov.l	@r15+,r6
	mov.l	@r15+,r5
	mov.l	@r15+,r4
	mov.l	@r15+,r3
	rts
	mov.l	@r15+,r2
	.align	1
.Lg_ffff: .word	0xFFFF
	.align	2
.Lg_ps:	.long	pstate
.Lg_nc:	.long	NCOLS
.Lg_8:	.long	0x00080000
.Lg_tune:	.long	tune

!@chunk pulse
! Replaces the SGL slSetSprite call inside the game's sprite helper 0x0601FDF8 (literal at
! 0x0601FEBC). r4 = SPRITE struct (VDP1 command image), r5 = Z. When the helper was called
! from the balloon loop for the column under the paddle, the sprite gets Gouraud shading
! with one of SGL's uniform ramp tables at VRAM 0x25C7FF00 (index k -> GRDA 0xFFE0 + k).
! Live registers from the callers: r14 = helper frame (@r14 = its return address,
! @(4,r14) = balloon loop frame, column at +16), r12 = player struct. Uses r0-r3, r6, r7.
pulse_emit:
	mov.l	.Lpe_tune,r0
	mov.b	@(T_FLAGS,r0),r0
	tst	#8,r0
	bt	.Lpe_clr
	mov.l	@r14,r1			! where the helper returns to
	mov.l	.Lpe_site,r2
	sub	r2,r1			! 0, 0x22, 0x80 or 0x98: the four balloon draws
	tst	r1,r1
	bt	.Lpe_ok
	mov	r1,r0
	cmp/eq	#0x22,r0
	bt	.Lpe_ok
	mov.w	.Lpe_80,r2
	cmp/eq	r2,r1
	bt	.Lpe_ok
	mov.w	.Lpe_98,r2
	cmp/eq	r2,r1
	bf	.Lpe_clr
.Lpe_ok:
	mov.l	@(P_CPU,r12),r0
	cmp/eq	#1,r0
	bt	.Lpe_clr
	mov.l	@(P_IDX,r12),r0
	mov	#2,r1
	cmp/hs	r1,r0
	bt	.Lpe_clr
	shll2	r0
	shll2	r0
	shll	r0
	mov.l	.Lpe_ps,r6
	add	r0,r6			! state
	mov.b	@(S_TYPE,r6),r0
	extu.b	r0,r0
	mov	#2,r1
	cmp/hs	r1,r0
	bf	.Lpe_clr
	mov.w	@(S_POS,r6),r0
	extu.w	r0,r7
	mov.w	.Lpe_ffff,r1
	extu.w	r1,r1
	cmp/eq	r1,r7
	bt	.Lpe_clr
	shll	r7
	shlr8	r7			! target column = pos >> 7
	mov.l	.Lpe_nc,r1
	mov.l	@r1,r1
	add	#-1,r1
	cmp/gt	r1,r7
	bf	.Lpe_1
	mov	r1,r7
.Lpe_1:	mov.l	@(4,r14),r1		! balloon loop frame
	mov.l	@(16,r1),r1		! its column
	cmp/eq	r7,r1
	bf	.Lpe_clr
	! target column: Gouraud on, ramp index from the triangle table
	mov.w	@(4,r4),r0
	or	#4,r0
	mov.w	r0,@(4,r4)
	mov.l	.Lpe_phase,r1
	mov.b	@r1,r0
	shlr2	r0			! step 0..11
	mov.l	.Lpe_tab,r1
	mov.b	@(r0,r1),r2
	extu.b	r2,r2
	mov.w	.Lpe_grda,r0
	add	r2,r0
	mov.w	r0,@(28,r4)
	mov.l	.Lpe_dirty,r1
	mov	#1,r0
	bra	.Lpe_go
	mov.b	r0,@r1
.Lpe_clr:
	! not ours: drop a gouraud bit we left in the shared struct
	mov.l	.Lpe_dirty,r1
	mov.b	@r1,r0
	tst	r0,r0
	bt	.Lpe_go
	mov	#0,r0
	mov.b	r0,@r1
	mov.w	@(28,r4),r0
	mov.w	.Lpe_grda,r2
	extu.w	r0,r0
	extu.w	r2,r2
	sub	r2,r0
	mov	#32,r2
	cmp/hs	r2,r0			! GRDA outside the ramp: not ours, keep it
	bt	.Lpe_go
	mov.w	@(4,r4),r0
	mov	r0,r2
	and	#7,r0
	cmp/eq	#4,r0
	bf	.Lpe_go
	mov	#-5,r0			! ~4
	and	r0,r2
	mov	r2,r0
	mov.w	r0,@(4,r4)
.Lpe_go:
	mov.l	.Lpe_orig,r0
	jmp	@r0
	nop
	.align	1
.Lpe_80:   .word	0x80
.Lpe_98:   .word	0x98
.Lpe_ffff: .word	0xFFFF
.Lpe_grda: .word	0xFFE0
	.align	2
.Lpe_tune:	.long	tune
.Lpe_site:	.long	0x06004538
.Lpe_ps:	.long	pstate
.Lpe_nc:	.long	NCOLS
.Lpe_phase:	.long	pulse_phase
.Lpe_tab:	.long	pulse_tab
.Lpe_dirty:	.long	pulse_dirty
.Lpe_orig:	.long	0x0604F88C
