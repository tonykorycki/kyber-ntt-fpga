# scripts/vivado_impl.tcl — Full Vivado implementation: project creation through bitstream
#
# Prerequisites: HLS IP must be exported to vivado/ip_repo/ first (make hls-synth)
# Run via: make vivado-impl  (invokes this through scripts/run_vivado_win.py)
#
# Recreates the Vivado project from scratch each run (-force). If a previous
# bitstream exists it is backed up to build/vivado/ before the project is deleted,
# so a mid-build crash does not destroy the last known-good output.
# Logs go to build/vivado/.

set root     [file normalize [file dirname [file dirname [info script]]]]
set proj_dir $root/vivado/proj/ntt_accel
set ip_repo  $root/vivado/ip_repo
set bd_tcl   $root/vivado/ntt_bd.tcl
set log_dir  $root/build/vivado

puts "=== vivado_impl.tcl ==="
puts "  root     : $root"
puts "  ip_repo  : $ip_repo"
puts "  proj_dir : $proj_dir"

# Sanity-check: HLS IP must exist before continuing
set ip_files [glob -nocomplain $ip_repo/*.zip $ip_repo/*/component.xml]
if {$ip_files eq ""} {
    error "No HLS IP found in $ip_repo — run 'make hls-synth' first"
}

# Back up the previous bitstream before nuking the project, so a crash
# mid-build doesn't destroy the last known-good output.
set prev_bit $proj_dir/ntt_accel.runs/impl_1/ntt_bd_wrapper.bit
if {[file exists $prev_bit]} {
    file mkdir $log_dir
    file copy -force $prev_bit $log_dir/ntt_bd_wrapper.bit.bak
    puts "  Backed up previous bitstream to $log_dir/ntt_bd_wrapper.bit.bak"
}

# Create project (recreate from scratch for clean state)
create_project -force ntt_accel $proj_dir -part xc7z020clg400-1

# Register HLS IP so ntt_bd.tcl can find xilinx.com:hls:ntt_top:1.0
set_property ip_repo_paths $ip_repo [current_project]
update_ip_catalog

# Recreate block design from checked-in TCL
source $bd_tcl

# Generate HDL and HWH from the block design
generate_target all [get_files ntt_bd.bd]

# Create and add the top-level HDL wrapper
set wrapper [make_wrapper -files [get_files ntt_bd.bd] -top]
add_files -norecurse $wrapper
set_property top ntt_bd_wrapper [current_fileset]
update_compile_order -fileset sources_1

puts ""
puts "=== Running synthesis ==="
launch_runs synth_1 -jobs 4
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    error "Synthesis failed — see $proj_dir/ntt_accel.runs/synth_1/runme.log"
}
puts "Synthesis complete."

puts ""
puts "=== Running implementation + bitstream ==="
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    error "Implementation failed — see $proj_dir/ntt_accel.runs/impl_1/runme.log"
}

# Re-export block design TCLe
open_bd_design [get_files ntt_bd.bd]
update_compile_order -fileset sources_1
write_bd_tcl -force $bd_tcl
puts "Block design TCL updated: $bd_tcl"

puts ""
puts "=== Done ==="
puts "  Bitstream : $proj_dir/ntt_accel.runs/impl_1/ntt_bd_wrapper.bit"
puts "  HWH       : $proj_dir/ntt_accel.gen/sources_1/bd/ntt_bd/hw_handoff/ntt_bd.hwh"
puts "  BD TCL    : $bd_tcl"
puts "  Run 'make export' to copy outputs to bitstream/"
