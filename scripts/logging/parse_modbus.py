#!/usr/bin/env python3
import argparse
import pyshark
import csv
import sys

def main():
    p = argparse.ArgumentParser(
        description="Parse every Modbus-TCP frame into CSV (no skips)")
    p.add_argument("-i","--input", required=True, help="Input PCAP file")
    p.add_argument("-o","--output",required=True, help="Output CSV file")
    args = p.parse_args()

    # Capture only Modbus frames
    try:
        cap = pyshark.FileCapture(args.input, display_filter="modbus")
    except Exception as e:
        print(f"ERROR opening pcap: {e}", file=sys.stderr)
        sys.exit(1)

    # Define our columns
    fieldnames = ["timestamp","func_code","registers","coils"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for pkt in cap:
            row = {k:"" for k in fieldnames}
            # timestamp
            row["timestamp"] = pkt.sniff_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            # modbus layer
            mb = pkt.modbus
            row["func_code"] = getattr(mb, "func_code", "")
            # registers (holding or input)
            regs = getattr(mb, "register_value", None)
            if regs:
                # pyshark returns list for multi-values
                row["registers"] = ";".join(regs) if isinstance(regs, list) else regs
            # coils
            coils = getattr(mb, "coil", None) or getattr(mb, "coil_value", None)
            if coils:
                row["coils"] = ";".join(coils) if isinstance(coils, list) else coils

            writer.writerow(row)

    print(f"Done. Parsed all Modbus frames to {args.output}")

if __name__ == "__main__":
    main()
