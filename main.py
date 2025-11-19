from uvm_pygen.loader import ConfigLoader


if __name__ == "__main__":
    # Load configurations
    loader = ConfigLoader(
        dut_config_path="config_dut.yaml",
        uvm_config_path="config_uvm.yaml"
    )
    
    # Validate
    loader.validate()
    
    # Print summary
    loader.summary()
    
    # Example: Access DUT information
    print("\n" + "="*60)
    print("EXAMPLE QUERIES")
    print("="*60)
    
    # Get operation enum
    op_enum = loader.dut.get_enum('operation_t')
    print(f"\nOperation enum has {len(op_enum.values)} operations:")
    for op_val in op_enum.values[:5]:  # First 5
        print(f"  {op_val.value}: {op_val.name} - {op_val.description}")
    
    # Get specific operation behavior
    mult_op = loader.dut.get_operation('MULT')
    if mult_op:
        print(f"\nMULT operation:")
        print(f"  Formula: {mult_op.formula}")
        print(f"  Output width: {mult_op.output_width}")
        print(f"  Latency: {mult_op.latency}")
    
    # Get control ports
    print(f"\nControl ports:")
    for port in loader.dut.get_control_ports():
        width = loader.dut.resolve_width(port.width)
        print(f"  {port.name}[{width-1}:0]: {port.description}")
    
    # Get test configuration
    random_test = loader.uvm.get_test('random_test')
    if random_test:
        print(f"\nRandom test configuration:")
        print(f"  Sequence: {random_test.sequence}")
        print(f"  Transaction count: {random_test.transaction_count}")
        print(f"  Timeout: {random_test.timeout} ns")