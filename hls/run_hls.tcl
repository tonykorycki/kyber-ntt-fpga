# hls/run_hls.tcl — Vitis HLS flow for the ntt_top IP
#
# Default: full project (set_top ntt_top, all sources, tb_ntt_top csim)
# Unit test: set HLS_MODE env var to select a module
#
# Usage (from repo root via make):
#   make hls-csim-barrett      # barrett unit test
#   make hls-csim-ntt-engine   # ntt_engine unit test
#   make hls-csim-twist        # twist unit test
#   make hls-csim-pointwise    # pointwise unit test
#   make hls-csim              # full project csim
#   make hls-synth             # full project csim + synthesis

set root [file normalize [file dirname [file dirname [info script]]]]
set mode [expr {[info exists ::env(HLS_MODE)] ? $::env(HLS_MODE) : ""}]

# --- Determine project configuration based on mode ---
switch $mode {
    barrett {
        set proj_name   barrett_unit
        set top_func    barrett_mul
        set sources     [list $root/hls/src/barrett.cpp]
        set tb          $root/hls/tb/tb_barrett.cpp
        set do_synth    0
    }
    ntt_engine {
        set proj_name   ntt_engine_unit
        set top_func    ntt_engine
        set sources     [list $root/hls/src/barrett.cpp \
                              $root/hls/src/ntt_engine.cpp]
        set tb          $root/hls/tb/tb_ntt_engine.cpp
        set do_synth    0
    }
    twist {
        set proj_name   twist_unit
        set top_func    twist
        set sources     [list $root/hls/src/barrett.cpp \
                              $root/hls/src/twist.cpp]
        set tb          $root/hls/tb/tb_twist.cpp
        set do_synth    0
    }
    pointwise {
        set proj_name   pointwise_unit
        set top_func    pointwise_mul
        set sources     [list $root/hls/src/barrett.cpp \
                              $root/hls/src/pointwise.cpp]
        set tb          $root/hls/tb/tb_pointwise.cpp
        set do_synth    0
    }
    default {
        # Full project — synthesizes the IP that Vivado imports
        set proj_name   ntt_hls
        set top_func    ntt_top
        set sources     [list $root/hls/src/barrett.cpp \
                              $root/hls/src/ntt_engine.cpp \
                              $root/hls/src/twist.cpp \
                              $root/hls/src/pointwise.cpp \
                              $root/hls/src/ntt_top.cpp]
        set tb          $root/hls/tb/tb_ntt_top.cpp
        set do_synth    [expr {$mode eq "synth"}]
    }
}

# --- Project setup ---
open_project -reset $root/build/hls/$proj_name
set_top $top_func

foreach f $sources { add_files $f }
add_files -tb $tb

open_solution -reset solution1
set_part xc7z020clg400-1
create_clock -period 10

# --- Run ---
csim_design

if {$do_synth} {
    csynth_design
    export_design -format ip_catalog -output $root/vivado/ip_repo
}

close_project
