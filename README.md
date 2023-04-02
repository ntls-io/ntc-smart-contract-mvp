# Development Setup

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install [Algorand sandbox](https://github.com/algorand/sandbox)
   and add this project folder as bind volume in sandbox `docker-compose.yml` under key `services.algod`:
   ```yml
   volumes:
     - type: bind
       source: <path>
       target: /data
   ```
3. Start sandbox:
   ```txt
   $ ./sandbox up
   ```
4. Install Python virtual environment (Python 3.10+) in project folder:
   ```txt
   $ python -m venv venv
   $ source ./venv/Scripts/activate # Windows
   $ source ./venv/bin/activate # Linux
   ```
5. Use Python interpreter: `./venv/Scripts/python.exe`
   VSCode: `Python: Select Interpreter`
   
6. Install dependencies:
   ```txt
   $ pip install -r requirements.txt
   ```
7. Set PythonPath :
   ```txt
   $ export PYTHONPATH=.
   ```
8. Run Deployment Test:
   ```txt
   $ python python_sdk/test_methods.py 
   ```

When finished, the sandbox can be stopped with ./sandbox down

# Interact with Smart Contract Manually

## General Calls
These are general calls made to your sandboxed algorand blockchain using the [`goal`](https://developer.algorand.org/docs/clis/goal/goal/#:~:text=GOAL%20is%20the%20CLI%20for,a%20different%20version%20of%20algod.) cli. Please enter the sandbox to execute these commands.
### See global variables of smart contract
```txt
goal app read --global --app-id $APP_ID --guess-format
```

### See application info of smart contract
```txt
goal app info --app-id $APP_ID
```

### See account info of the smart contract (or other accounts)
```txt
goal account info -a $ACCOUNT_APP
```

### See local variables of opted in accounts
```txt
goal app read --local --from $ACCOUNT_2 --app-id $APP_ID
```


# Links

- [Youtube Pyteal Course](https://youtube.com/playlist?list=PLpAdAjL5F75CNnmGbz9Dm_k-z5I6Sv9_x)
- [Official Algorand Smart Contract Guidelines](https://developer.algorand.org/docs/get-details/dapps/avm/teal/guidelines/)
- [PyTeal Documentation](https://pyteal.readthedocs.io/en/latest/index.html)
- [Algorand DevRel Example Contracts](https://github.com/algorand/smart-contracts)
