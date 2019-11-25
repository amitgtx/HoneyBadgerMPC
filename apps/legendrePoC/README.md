Instructions for executing Legendre based Proof of Custody scheme
==
This readme contains instructions on how to execute [`legendreprf.py`](./legendreprf.py) which implements the recently proposed [`legendre PRF based "Proof of Custody" scheme`](https://ethresear.ch/t/using-the-legendre-symbol-as-a-prf-for-the-proof-of-custody/5169). More details regarding the scheme and implementation is present in [`legendreprf.py`](./legendreprf.py)


Execution steps
--
- The first task is to set up the HoneyBadgerMPC environment. Follow [these instructions](../../docs/development/getting-started.rst#managing-your-development-environment-with-docker-compose) to set up the `docker-compose` development environment

- Then a shell session needs to be spawned in the development container, so run:
```
$ docker-compose run --rm honeybadgermpc bash
```

- Once you are inside the shell, execute the following command:
```
root@{containerid}:/usr/src/HoneyBadgerMPC# python apps/legendrePoC/legendreprf.py
```
and look for the output `Legendre PRF based Proof of Custody scheme ran successfully`