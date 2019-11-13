"""
hbMPC tutorial 1. Running sample MPC programs in the testing simulator
"""
import asyncio
from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.progs.mixins.dataflow import Share
from honeybadgermpc.preprocessing import (
    PreProcessedElements as FakePreProcessedElements,
)
from honeybadgermpc.utils.typecheck import TypeCheck
from honeybadgermpc.progs.mixins.share_arithmetic import (
    MixinConstants,
    BeaverMultiply,
    BeaverMultiplyArrays,
)

config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply(),
}


async def eval(ctx, powers_of_k_shares, X):
    coeff = [ctx.field(1)]

    for Xi in X:
        shift_coeff = coeff + [ctx.field(0)]
        mult_coeff = [ctx.field(0)] + [elem * Xi for elem in coeff]
        coeff = [i + j for i, j in zip(shift_coeff, mult_coeff)]

    # print(f"[{ctx.myid}] Inside EVAL : ", coeff)
    # print(f"[{ctx.myid}] Inside EVAL : ", str(powers_of_k_shares))

    y = coeff[len(coeff) - 1]
    # y = ctx.ShareFuture()
    B = len(coeff) - 1
    for i in range(B):
        y = y + powers_of_k_shares[i] * coeff[B - 1 - i]

    # print(f"[{ctx.myid}] Inside EVAL : ", y)

    return y


async def prf(ctx, y: Share):
    
    p = y.v.modulus
    exponent =  int ((p - 1) / 2)
    res = ctx.ShareFuture()
    res.set_result(ctx.Share(1))

    while exponent > 0:
        if(exponent & 1):
            res = res * y
        y = y * y
        exponent = exponent >> 1

    return res


def verify(ctx, mpcResult, K, X):

    Y = ctx.field(1)
    p = Y.modulus
    exponent = int((p - 1) / 2)

    for Xi in X:
        Y *= (K + Xi)

    expectedResult = ctx.field(1)

    while exponent > 0:
        if(exponent & 1):
            expectedResult *= Y
        Y = Y * Y
        exponent = exponent >> 1

    return mpcResult == expectedResult





async def prog(ctx):
    
    K = ctx.field(77)  # Secret key
    B = 6
    _X = [21, 88, 97, 33, 44, 83]  # B=6 random field elements
    X = [ctx.field(Xi) for Xi in _X]
 
    powers_of_k_shares = [ctx.Share(K ** i) for i in range(1, B+1)]

    print(f"[{ctx.myid}] Precompute OK")


    y = await eval(ctx, powers_of_k_shares, X)
    print(f"[{ctx.myid}] Eval OK", y, type(y))


    fk_x = await prf(ctx, y)
    print(f"[{ctx.myid}] PRF OK", fk_x, type(fk_x))


    FK_x = await fk_x.open()
    print(f"[{ctx.myid}] Opening OK", FK_x, type(FK_x))


    assert verify(ctx, FK_x, K, X) == True
    print(f"[{ctx.myid}] Verify OK")



    # powers_of_k = await precompute(ctx, k)



async def legendrePRF_challenge():
    # Create a test network of 4 nodes (no sockets, just asyncio tasks)
    n, t = 4, 1
    K = 77  # Secret key
    B = 6
    pp = FakePreProcessedElements()
    pp.generate_triples(10000, n, t)


    program_runner = TaskProgramRunner(n, t, config)
    program_runner.add(prog)
    results = await program_runner.join()
    return results


def main():
    # Run the tutorials
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(legendrePRF_challenge())
    # loop.run_until_complete(tutorial_2())


if __name__ == "__main__":
    main()
    print("Legendre PRF challenge ran successfully")













