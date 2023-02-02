import importlib
import sys

from contracts.pyteal_helpers import program

if __name__ == "__main__":
    mod = sys.argv[1]

    try:
        approval_out = sys.argv[2] #reads in two output files. approval 
    except IndexError:
        approval_out = None

    try:
        clear_out = sys.argv[3] #and clear files
    except IndexError:
        clear_out = None

    contract = importlib.import_module(mod) # reads in a module

    if approval_out is None:
        print(program.application(contract.approval())) # calls the approval function
    else:
        with open(approval_out, "w") as h:
            h.write(program.application(contract.approval()))

    if clear_out is not None:
        with open(clear_out, "w") as h:
            h.write(program.application(contract.clear())) #calls the clear function and write them to the output files
