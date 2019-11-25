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
    BeaverMultiplyArrays
)

from honeybadgermpc.progs.mixins.share_comparison import MixinConstants, Equality, LessThan

config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply(),
    MixinConstants.ShareEquality: Equality()
}


async def linear_search(ctx, key: Share, A):
    
    for a in A:
        flag = (await (a == key).open()):
        # flag = 3
        if (flag != 0):
            return a, 1
    return -1, 0



async def prog(ctx):
    
    _A = [10, 30, 50, 70, 90, 150]
    # A = [ctx.Share(a) + ctx.preproc.get_zero(ctx) for a in _A]
    A = [ctx.Share(a) for a in _A]
    # L = [int(a.v) % 10000 for a in A]
    # print(f"[{ctx.myid}] A = ", L)


    K = 700
    k = ctx.Share(K) + ctx.preproc.get_zero(ctx)
    print(f"[{ctx.myid}] Result = ", index, result)


    index, result = await linear_search(ctx, k, A)

    print(f"[{ctx.myid}] Result = ", index, result)


async def continuous_double_auction():
    # Create a test network of 4 nodes (no sockets, just asyncio tasks)
    n, t = 4, 1
    pp = FakePreProcessedElements()
    pp.generate_zeros(10000, n, t)
    pp.generate_triples(10000, n, t)
    pp.generate_bits(10000, n, t)
    program_runner = TaskProgramRunner(n, t, config)
    program_runner.add(prog)
    results = await program_runner.join()
    return results


def main():
    # Run the tutorials
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(continuous_double_auction())
    # loop.run_until_complete(tutorial_2())


if __name__ == "__main__":
    main()
    print("Continuous Double Auction ran successfully")
