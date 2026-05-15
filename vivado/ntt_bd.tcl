
################################################################
# This is a generated script based on design: ntt_bd
#
# Though there are limitations about the generated script,
# the main purpose of this utility is to make learning
# IP Integrator Tcl commands easier.
################################################################

namespace eval _tcl {
proc get_script_folder {} {
   set script_path [file normalize [info script]]
   set script_folder [file dirname $script_path]
   return $script_folder
}
}
variable script_folder
set script_folder [_tcl::get_script_folder]

################################################################
# Check if script is running in correct Vivado version.
################################################################
set scripts_vivado_version 2025.1
set current_vivado_version [version -short]

if { [string first $scripts_vivado_version $current_vivado_version] == -1 } {
   puts ""
   if { [string compare $scripts_vivado_version $current_vivado_version] > 0 } {
      catch {common::send_gid_msg -ssname BD::TCL -id 2042 -severity "ERROR" " This script was generated using Vivado <$scripts_vivado_version> and is being run in <$current_vivado_version> of Vivado. Sourcing the script failed since it was created with a future version of Vivado."}

   } else {
     catch {common::send_gid_msg -ssname BD::TCL -id 2041 -severity "ERROR" "This script was generated using Vivado <$scripts_vivado_version> and is being run in <$current_vivado_version> of Vivado. Please run the script in Vivado <$scripts_vivado_version> then open the design in Vivado <$current_vivado_version>. Upgrade the design by running \"Tools => Report => Report IP Status...\", then run write_bd_tcl to create an updated script."}

   }

   return 1
}

################################################################
# START
################################################################

# To test this script, run the following commands from Vivado Tcl console:
# source ntt_bd_script.tcl

# If there is no project opened, this script will create a
# project, but make sure you do not have an existing project
# <./myproj/project_1.xpr> in the current working folder.

set list_projs [get_projects -quiet]
if { $list_projs eq "" } {
   create_project project_1 myproj -part xc7z020clg400-1
}


# CHANGE DESIGN NAME HERE
variable design_name
set design_name ntt_bd

# If you do not already have an existing IP Integrator design open,
# you can create a design using the following command:
#    create_bd_design $design_name

# Creating design if needed
set errMsg ""
set nRet 0

set cur_design [current_bd_design -quiet]
set list_cells [get_bd_cells -quiet]

if { ${design_name} eq "" } {
   # USE CASES:
   #    1) Design_name not set

   set errMsg "Please set the variable <design_name> to a non-empty value."
   set nRet 1

} elseif { ${cur_design} ne "" && ${list_cells} eq "" } {
   # USE CASES:
   #    2): Current design opened AND is empty AND names same.
   #    3): Current design opened AND is empty AND names diff; design_name NOT in project.
   #    4): Current design opened AND is empty AND names diff; design_name exists in project.

   if { $cur_design ne $design_name } {
      common::send_gid_msg -ssname BD::TCL -id 2001 -severity "INFO" "Changing value of <design_name> from <$design_name> to <$cur_design> since current design is empty."
      set design_name [get_property NAME $cur_design]
   }
   common::send_gid_msg -ssname BD::TCL -id 2002 -severity "INFO" "Constructing design in IPI design <$cur_design>..."

} elseif { ${cur_design} ne "" && $list_cells ne "" && $cur_design eq $design_name } {
   # USE CASES:
   #    5) Current design opened AND has components AND same names.

   set errMsg "Design <$design_name> already exists in your project, please set the variable <design_name> to another value."
   set nRet 1
} elseif { [get_files -quiet ${design_name}.bd] ne "" } {
   # USE CASES: 
   #    6) Current opened design, has components, but diff names, design_name exists in project.
   #    7) No opened design, design_name exists in project.

   set errMsg "Design <$design_name> already exists in your project, please set the variable <design_name> to another value."
   set nRet 2

} else {
   # USE CASES:
   #    8) No opened design, design_name not in project.
   #    9) Current opened design, has components, but diff names, design_name not in project.

   common::send_gid_msg -ssname BD::TCL -id 2003 -severity "INFO" "Currently there is no design <$design_name> in project, so creating one..."

   create_bd_design $design_name

   common::send_gid_msg -ssname BD::TCL -id 2004 -severity "INFO" "Making design <$design_name> as current_bd_design."
   current_bd_design $design_name

}

common::send_gid_msg -ssname BD::TCL -id 2005 -severity "INFO" "Currently the variable <design_name> is equal to \"$design_name\"."

if { $nRet != 0 } {
   catch {common::send_gid_msg -ssname BD::TCL -id 2006 -severity "ERROR" $errMsg}
   return $nRet
}

set bCheckIPsPassed 1
##################################################################
# CHECK IPs
##################################################################
set bCheckIPs 1
if { $bCheckIPs == 1 } {
   set list_check_ips "\ 
xilinx.com:hls:ntt_top:1.0\
xilinx.com:ip:processing_system7:5.5\
xilinx.com:ip:blk_mem_gen:8.4\
xilinx.com:ip:axi_bram_ctrl:4.1\
xilinx.com:ip:axi_gpio:2.0\
xilinx.com:ip:smartconnect:1.0\
xilinx.com:ip:proc_sys_reset:5.0\
xilinx.com:ip:xlconcat:2.1\
xilinx.com:ip:xlconstant:1.1\
"

   set list_ips_missing ""
   common::send_gid_msg -ssname BD::TCL -id 2011 -severity "INFO" "Checking if the following IPs exist in the project's IP catalog: $list_check_ips ."

   foreach ip_vlnv $list_check_ips {
      set ip_obj [get_ipdefs -all $ip_vlnv]
      if { $ip_obj eq "" } {
         lappend list_ips_missing $ip_vlnv
      }
   }

   if { $list_ips_missing ne "" } {
      catch {common::send_gid_msg -ssname BD::TCL -id 2012 -severity "ERROR" "The following IPs are not found in the IP Catalog:\n  $list_ips_missing\n\nResolution: Please add the repository containing the IP(s) to the project." }
      set bCheckIPsPassed 0
   }

}

if { $bCheckIPsPassed != 1 } {
  common::send_gid_msg -ssname BD::TCL -id 2023 -severity "WARNING" "Will not continue with creation of design due to the error(s) above."
  return 3
}

##################################################################
# DESIGN PROCs
##################################################################



# Procedure to create entire design; Provide argument to make
# procedure reusable. If parentCell is "", will use root.
proc create_root_design { parentCell } {

  variable script_folder
  variable design_name

  if { $parentCell eq "" } {
     set parentCell [get_bd_cells /]
  }

  # Get object for parentCell
  set parentObj [get_bd_cells $parentCell]
  if { $parentObj == "" } {
     catch {common::send_gid_msg -ssname BD::TCL -id 2090 -severity "ERROR" "Unable to find parent cell <$parentCell>!"}
     return
  }

  # Make sure parentObj is hier blk
  set parentType [get_property TYPE $parentObj]
  if { $parentType ne "hier" } {
     catch {common::send_gid_msg -ssname BD::TCL -id 2091 -severity "ERROR" "Parent <$parentObj> has TYPE = <$parentType>. Expected to be <hier>."}
     return
  }

  # Save current instance; Restore later
  set oldCurInst [current_bd_instance .]

  # Set parent object as current
  current_bd_instance $parentObj


  # Create interface ports

  # Create ports

  # Create instance: ntt_top_0, and set properties
  set ntt_top_0 [ create_bd_cell -type ip -vlnv xilinx.com:hls:ntt_top:1.0 ntt_top_0 ]

  # Create instance: processing_system7_0, and set properties
  set processing_system7_0 [ create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0 ]
  set_property -dict [list \
    CONFIG.PCW_ACT_APU_PERIPHERAL_FREQMHZ {666.666687} \
    CONFIG.PCW_ACT_CAN_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_DCI_PERIPHERAL_FREQMHZ {10.158730} \
    CONFIG.PCW_ACT_ENET0_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_ENET1_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ {100.000000} \
    CONFIG.PCW_ACT_FPGA1_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_FPGA2_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_FPGA3_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_PCAP_PERIPHERAL_FREQMHZ {200.000000} \
    CONFIG.PCW_ACT_QSPI_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_SDIO_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_SMC_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_SPI_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_TPIU_PERIPHERAL_FREQMHZ {200.000000} \
    CONFIG.PCW_ACT_TTC0_CLK0_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_ACT_TTC0_CLK1_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_ACT_TTC0_CLK2_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_ACT_TTC1_CLK0_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_ACT_TTC1_CLK1_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_ACT_TTC1_CLK2_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_ACT_UART_PERIPHERAL_FREQMHZ {10.000000} \
    CONFIG.PCW_ACT_WDT_PERIPHERAL_FREQMHZ {111.111115} \
    CONFIG.PCW_CLK0_FREQ {100000000} \
    CONFIG.PCW_CLK1_FREQ {10000000} \
    CONFIG.PCW_CLK2_FREQ {10000000} \
    CONFIG.PCW_CLK3_FREQ {10000000} \
    CONFIG.PCW_DDR_RAM_HIGHADDR {0x1FFFFFFF} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
    CONFIG.PCW_FPGA_FCLK0_ENABLE {1} \
    CONFIG.PCW_UIPARAM_ACT_DDR_FREQ_MHZ {533.333374} \
    CONFIG.PCW_USE_AXI_NONSECURE {1} \
  ] $processing_system7_0


  # Create instance: bram_a, and set properties
  set bram_a [ create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 bram_a ]
  set_property -dict [list \
    CONFIG.Memory_Type {True_Dual_Port_RAM} \
    CONFIG.Operating_Mode_A {WRITE_FIRST} \
    CONFIG.Operating_Mode_B {WRITE_FIRST} \
    CONFIG.Register_PortA_Output_of_Memory_Primitives {false} \
    CONFIG.Register_PortB_Output_of_Memory_Primitives {false} \
    CONFIG.Write_Width_B {32} \
    CONFIG.use_bram_block {BRAM_Controller} \
  ] $bram_a


  # Create instance: axi_bram_a, and set properties
  set axi_bram_a [ create_bd_cell -type ip -vlnv xilinx.com:ip:axi_bram_ctrl:4.1 axi_bram_a ]
  set_property CONFIG.SINGLE_PORT_BRAM {1} $axi_bram_a


  # Create instance: bram_c, and set properties
  set bram_c [ create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 bram_c ]
  set_property -dict [list \
    CONFIG.Memory_Type {True_Dual_Port_RAM} \
    CONFIG.Operating_Mode_A {WRITE_FIRST} \
    CONFIG.Operating_Mode_B {WRITE_FIRST} \
    CONFIG.Register_PortA_Output_of_Memory_Primitives {false} \
    CONFIG.Register_PortB_Output_of_Memory_Primitives {false} \
    CONFIG.Write_Width_B {32} \
    CONFIG.use_bram_block {BRAM_Controller} \
  ] $bram_c


  # Create instance: bram_b, and set properties
  set bram_b [ create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 bram_b ]
  set_property -dict [list \
    CONFIG.Memory_Type {True_Dual_Port_RAM} \
    CONFIG.Operating_Mode_A {WRITE_FIRST} \
    CONFIG.Operating_Mode_B {WRITE_FIRST} \
    CONFIG.Register_PortA_Output_of_Memory_Primitives {false} \
    CONFIG.Register_PortB_Output_of_Memory_Primitives {false} \
    CONFIG.Write_Width_B {32} \
    CONFIG.use_bram_block {BRAM_Controller} \
  ] $bram_b


  # Create instance: axi_bram_c, and set properties
  set axi_bram_c [ create_bd_cell -type ip -vlnv xilinx.com:ip:axi_bram_ctrl:4.1 axi_bram_c ]
  set_property CONFIG.SINGLE_PORT_BRAM {1} $axi_bram_c


  # Create instance: axi_bram_b, and set properties
  set axi_bram_b [ create_bd_cell -type ip -vlnv xilinx.com:ip:axi_bram_ctrl:4.1 axi_bram_b ]
  set_property CONFIG.SINGLE_PORT_BRAM {1} $axi_bram_b


  # Create instance: axi_gpio_0, and set properties
  set axi_gpio_0 [ create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 axi_gpio_0 ]
  set_property -dict [list \
    CONFIG.C_ALL_INPUTS_2 {1} \
    CONFIG.C_ALL_OUTPUTS {1} \
    CONFIG.C_GPIO2_WIDTH {2} \
    CONFIG.C_GPIO_WIDTH {1} \
    CONFIG.C_IS_DUAL {1} \
  ] $axi_gpio_0


  # Create instance: axi_smc, and set properties
  set axi_smc [ create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_smc ]
  set_property -dict [list \
    CONFIG.NUM_MI {4} \
    CONFIG.NUM_SI {1} \
  ] $axi_smc


  # Create instance: rst_ps7_0_100M, and set properties
  set rst_ps7_0_100M [ create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 rst_ps7_0_100M ]

  # Create instance: xlconcat_ap, and set properties
  set xlconcat_ap [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 xlconcat_ap ]

  # Create instance: xlconcat_a, and set properties
  set xlconcat_a [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 xlconcat_a ]
  set_property CONFIG.NUM_PORTS {4} $xlconcat_a


  # Create instance: xlconcat_c, and set properties
  set xlconcat_c [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 xlconcat_c ]
  set_property CONFIG.NUM_PORTS {4} $xlconcat_c


  # Create instance: xlconcat_b, and set properties
  set xlconcat_b [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 xlconcat_b ]
  set_property CONFIG.NUM_PORTS {4} $xlconcat_b


  # Create instance: xlconstant_bram_rtsb, and set properties
  set xlconstant_bram_rtsb [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 xlconstant_bram_rtsb ]
  set_property CONFIG.CONST_VAL {0} $xlconstant_bram_rtsb


  # Create instance: const00_a, and set properties
  set const00_a [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const00_a ]
  set_property -dict [list \
    CONFIG.CONST_VAL {0} \
    CONFIG.CONST_WIDTH {2} \
  ] $const00_a


  # Create instance: lshift2_a, and set properties
  set lshift2_a [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 lshift2_a ]
  set_property -dict [list \
    CONFIG.IN0_WIDTH {2} \
    CONFIG.IN1_WIDTH {8} \
    CONFIG.NUM_PORTS {2} \
  ] $lshift2_a


  # Create instance: lshift2_b, and set properties
  set lshift2_b [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 lshift2_b ]
  set_property -dict [list \
    CONFIG.IN0_WIDTH {2} \
    CONFIG.IN1_WIDTH {8} \
    CONFIG.NUM_PORTS {2} \
  ] $lshift2_b


  # Create instance: lshift2_c, and set properties
  set lshift2_c [ create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 lshift2_c ]
  set_property -dict [list \
    CONFIG.IN0_WIDTH {2} \
    CONFIG.IN1_WIDTH {8} \
    CONFIG.NUM_PORTS {2} \
  ] $lshift2_c


  # Create interface connections
  connect_bd_intf_net -intf_net axi_bram_a_BRAM_PORTA [get_bd_intf_pins axi_bram_a/BRAM_PORTA] [get_bd_intf_pins bram_a/BRAM_PORTA]
  connect_bd_intf_net -intf_net axi_bram_b_BRAM_PORTA [get_bd_intf_pins axi_bram_b/BRAM_PORTA] [get_bd_intf_pins bram_b/BRAM_PORTA]
  connect_bd_intf_net -intf_net axi_bram_c_BRAM_PORTA [get_bd_intf_pins axi_bram_c/BRAM_PORTA] [get_bd_intf_pins bram_c/BRAM_PORTA]
  connect_bd_intf_net -intf_net axi_smc_M00_AXI [get_bd_intf_pins axi_smc/M00_AXI] [get_bd_intf_pins axi_bram_a/S_AXI]
  connect_bd_intf_net -intf_net axi_smc_M01_AXI [get_bd_intf_pins axi_smc/M01_AXI] [get_bd_intf_pins axi_bram_b/S_AXI]
  connect_bd_intf_net -intf_net axi_smc_M02_AXI [get_bd_intf_pins axi_smc/M02_AXI] [get_bd_intf_pins axi_bram_c/S_AXI]
  connect_bd_intf_net -intf_net axi_smc_M03_AXI [get_bd_intf_pins axi_smc/M03_AXI] [get_bd_intf_pins axi_gpio_0/S_AXI]
  connect_bd_intf_net -intf_net processing_system7_0_M_AXI_GP0 [get_bd_intf_pins processing_system7_0/M_AXI_GP0] [get_bd_intf_pins axi_smc/S00_AXI]

  # Create port connections
  connect_bd_net -net Net  [get_bd_pins ntt_top_0/b_we0] \
  [get_bd_pins xlconcat_b/In0] \
  [get_bd_pins xlconcat_b/In1] \
  [get_bd_pins xlconcat_b/In2] \
  [get_bd_pins xlconcat_b/In3]
  connect_bd_net -net Net1  [get_bd_pins ntt_top_0/c_we0] \
  [get_bd_pins xlconcat_c/In0] \
  [get_bd_pins xlconcat_c/In1] \
  [get_bd_pins xlconcat_c/In2] \
  [get_bd_pins xlconcat_c/In3]
  connect_bd_net -net axi_gpio_0_gpio_io_o  [get_bd_pins axi_gpio_0/gpio_io_o] \
  [get_bd_pins ntt_top_0/ap_start]
  connect_bd_net -net bram_a_doutb  [get_bd_pins bram_a/doutb] \
  [get_bd_pins ntt_top_0/a_q0]
  connect_bd_net -net bram_b_doutb  [get_bd_pins bram_b/doutb] \
  [get_bd_pins ntt_top_0/b_q0]
  connect_bd_net -net bram_c_doutb  [get_bd_pins bram_c/doutb] \
  [get_bd_pins ntt_top_0/c_q0]
  connect_bd_net -net const00_a_dout  [get_bd_pins const00_a/dout] \
  [get_bd_pins lshift2_a/In0] \
  [get_bd_pins lshift2_b/In0] \
  [get_bd_pins lshift2_c/In0]
  connect_bd_net -net lshift2_a_dout  [get_bd_pins lshift2_a/dout] \
  [get_bd_pins bram_a/addrb]
  connect_bd_net -net lshift2_b_dout  [get_bd_pins lshift2_b/dout] \
  [get_bd_pins bram_b/addrb]
  connect_bd_net -net lshift2_c_dout  [get_bd_pins lshift2_c/dout] \
  [get_bd_pins bram_c/addrb]
  connect_bd_net -net ntt_top_0_a_address0  [get_bd_pins ntt_top_0/a_address0] \
  [get_bd_pins lshift2_a/In1]
  connect_bd_net -net ntt_top_0_a_ce0  [get_bd_pins ntt_top_0/a_ce0] \
  [get_bd_pins bram_a/enb]
  connect_bd_net -net ntt_top_0_a_d0  [get_bd_pins ntt_top_0/a_d0] \
  [get_bd_pins bram_a/dinb]
  connect_bd_net -net ntt_top_0_a_we0  [get_bd_pins ntt_top_0/a_we0] \
  [get_bd_pins xlconcat_a/In0] \
  [get_bd_pins xlconcat_a/In1] \
  [get_bd_pins xlconcat_a/In2] \
  [get_bd_pins xlconcat_a/In3]
  connect_bd_net -net ntt_top_0_ap_done  [get_bd_pins ntt_top_0/ap_done] \
  [get_bd_pins xlconcat_ap/In0]
  connect_bd_net -net ntt_top_0_ap_idle  [get_bd_pins ntt_top_0/ap_idle] \
  [get_bd_pins xlconcat_ap/In1]
  connect_bd_net -net ntt_top_0_b_address0  [get_bd_pins ntt_top_0/b_address0] \
  [get_bd_pins lshift2_b/In1]
  connect_bd_net -net ntt_top_0_b_ce0  [get_bd_pins ntt_top_0/b_ce0] \
  [get_bd_pins bram_b/enb]
  connect_bd_net -net ntt_top_0_b_d0  [get_bd_pins ntt_top_0/b_d0] \
  [get_bd_pins bram_b/dinb]
  connect_bd_net -net ntt_top_0_c_address0  [get_bd_pins ntt_top_0/c_address0] \
  [get_bd_pins lshift2_c/In1]
  connect_bd_net -net ntt_top_0_c_ce0  [get_bd_pins ntt_top_0/c_ce0] \
  [get_bd_pins bram_c/enb]
  connect_bd_net -net ntt_top_0_c_d0  [get_bd_pins ntt_top_0/c_d0] \
  [get_bd_pins bram_c/dinb]
  connect_bd_net -net processing_system7_0_FCLK_CLK0  [get_bd_pins processing_system7_0/FCLK_CLK0] \
  [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK] \
  [get_bd_pins axi_smc/aclk] \
  [get_bd_pins axi_bram_a/s_axi_aclk] \
  [get_bd_pins rst_ps7_0_100M/slowest_sync_clk] \
  [get_bd_pins axi_bram_b/s_axi_aclk] \
  [get_bd_pins axi_bram_c/s_axi_aclk] \
  [get_bd_pins axi_gpio_0/s_axi_aclk] \
  [get_bd_pins ntt_top_0/ap_clk] \
  [get_bd_pins bram_a/clkb] \
  [get_bd_pins bram_b/clkb] \
  [get_bd_pins bram_c/clkb]
  connect_bd_net -net processing_system7_0_FCLK_RESET0_N  [get_bd_pins processing_system7_0/FCLK_RESET0_N] \
  [get_bd_pins rst_ps7_0_100M/ext_reset_in]
  connect_bd_net -net rst_ps7_0_100M_peripheral_aresetn  [get_bd_pins rst_ps7_0_100M/peripheral_aresetn] \
  [get_bd_pins axi_bram_a/s_axi_aresetn] \
  [get_bd_pins axi_smc/aresetn] \
  [get_bd_pins axi_bram_b/s_axi_aresetn] \
  [get_bd_pins axi_bram_c/s_axi_aresetn] \
  [get_bd_pins axi_gpio_0/s_axi_aresetn]
  connect_bd_net -net rst_ps7_0_100M_peripheral_reset  [get_bd_pins rst_ps7_0_100M/peripheral_reset] \
  [get_bd_pins ntt_top_0/ap_rst]
  connect_bd_net -net xlconcat_0_dout  [get_bd_pins xlconcat_ap/dout] \
  [get_bd_pins axi_gpio_0/gpio2_io_i]
  connect_bd_net -net xlconcat_1_dout  [get_bd_pins xlconcat_a/dout] \
  [get_bd_pins bram_a/web]
  connect_bd_net -net xlconcat_b_dout  [get_bd_pins xlconcat_b/dout] \
  [get_bd_pins bram_b/web]
  connect_bd_net -net xlconcat_c_dout  [get_bd_pins xlconcat_c/dout] \
  [get_bd_pins bram_c/web]
  connect_bd_net -net xlconstant_bram_rtsb_dout  [get_bd_pins xlconstant_bram_rtsb/dout] \
  [get_bd_pins bram_a/rstb] \
  [get_bd_pins bram_b/rstb] \
  [get_bd_pins bram_c/rstb]

  # Create address segments
  assign_bd_address -offset 0x40000000 -range 0x00002000 -target_address_space [get_bd_addr_spaces processing_system7_0/Data] [get_bd_addr_segs axi_bram_a/S_AXI/Mem0] -force
  assign_bd_address -offset 0x40002000 -range 0x00002000 -target_address_space [get_bd_addr_spaces processing_system7_0/Data] [get_bd_addr_segs axi_bram_b/S_AXI/Mem0] -force
  assign_bd_address -offset 0x40004000 -range 0x00002000 -target_address_space [get_bd_addr_spaces processing_system7_0/Data] [get_bd_addr_segs axi_bram_c/S_AXI/Mem0] -force
  assign_bd_address -offset 0x40010000 -range 0x00010000 -target_address_space [get_bd_addr_spaces processing_system7_0/Data] [get_bd_addr_segs axi_gpio_0/S_AXI/Reg] -force


  # Restore current instance
  current_bd_instance $oldCurInst

  validate_bd_design
  save_bd_design
}
# End of create_root_design()


##################################################################
# MAIN FLOW
##################################################################

create_root_design ""


