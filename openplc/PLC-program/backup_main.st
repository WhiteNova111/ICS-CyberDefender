
PROGRAM PLC_PRG
VAR
  x : BOOL;
END_VAR

(* Inverts Output Q0 each scan *)
x := NOT x;
Q0 := x;
END_PROGRAM
