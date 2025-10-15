// Auto-generated UVM environment for DUT: alu

class Alu_env extends uvm_env;
   `uvm_component_utils(Alu_env)

   
   input_agent input_agent_inst;
   
   output_agent output_agent_inst;
   

   
   scoreboard sb;
   

   function new(string name = "alu_env", uvm_component parent = null);
      super.new(name, parent);
   endfunction

endclass