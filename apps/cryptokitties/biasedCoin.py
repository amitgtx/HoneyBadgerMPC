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

# from honeybadgermpc.progs import fixedpoint

from honeybadgermpc.progs.fixedpoint import FixedPoint
from honeybadgermpc.progs.fixedpoint import F

from honeybadgermpc.progs.mixins.share_comparison import MixinConstants, Equality, LessThan


config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply(),
    MixinConstants.ShareLessThan: LessThan(),
    MixinConstants.ShareEquality: Equality()
}
# import numpy as np

F = 8

def create_secret_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(x * 2 ** F) + ctx.preproc.get_zero(ctx))

def create_clear_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(int(x * 2 ** F)))   


def convert_integer_ss_to_fixed_point_ss(ctx, integer_ss):

	scaled_integer_ss = integer_ss * 2 ** F

	return FixedPoint(ctx, scaled_integer_ss)


# Assumption - weight is a 8 bit value
async def flip_biased_coin(ctx, weight):

	bits = F

	# Normalizing weight to a real value in [0, 1]
	normalized_weight = await convert_integer_ss_to_fixed_point_ss(ctx, weight).div(2 ** bits)

	# Flipping a 8 bit fair coin  
	coin = ctx.Share(0)

	for i in range(bits):

		coin += 2**i * ctx.preproc.get_bit(ctx)

	# Normalizing coin value to a real value in [0, 1]
	normalized_coin = await convert_integer_ss_to_fixed_point_ss(ctx, coin).div(2 ** bits)

	result = await normalized_coin.lt(normalized_weight)

	return result



# Assumption - secret_param_1, secret_param_2 will be instantiated using some mom's and dad's gene attribute respectively
async def flip_biased_coin_2(ctx, secret_param_1, secret_param_2):

	# Flipping a biased coin based on 1st secret param
	coin1 = await flip_biased_coin(ctx, secret_param_1)

	# Flipping a biased coin based on 2nd secret param
	coin2 = await flip_biased_coin(ctx, secret_param_2)

	# final_coin = await (coin1 == coin2)

	# Combining both biased coins to get the final biased coin
	final_coin = await ((ctx.Share(1) - coin1) * coin2 + coin1 * (ctx.Share(1) - coin2)) 

	return final_coin



async def prog(ctx):

	# Number of biased coins that need to be flipped
	N = 10

	# Intializing Dad's and Mom's secret gene as some arbitrary numbers 
	dad = 25
	mom = 150

	for i in range(N):

		# Secret share of Dad's and Mom's gene
		# dad_ss = ctx.Share(dad) + ctx.preproc.get_zero(ctx)
		dad_ss = ctx.Share(dad)
		# mom_ss = ctx.Share(mom) + ctx.preproc.get_zero(ctx)
		mom_ss = ctx.Share(mom)


		# Flipping a biased coin whose secret parameters depend on parent genes
		coin_ss = await flip_biased_coin_2(ctx, dad_ss, mom_ss)

		# Opening the output
		coin = await coin_ss.open()


		print(f"[{ctx.myid}] Biased coin {i}: {coin}")




async def test_flip_biased_coin():
    # Create a test network of 4 nodes (no sockets, just asyncio tasks)
    n, t = 4, 1
    pp = FakePreProcessedElements()
    # pp.generate_zeros(10000, n, t)	
    pp.generate_triples(10000, n, t)
    # pp.generate_rands(10000, n, t)
    pp.generate_bits(10000, n, t)
    program_runner = TaskProgramRunner(n, t, config)
    program_runner.add(prog)
    results = await program_runner.join()
    return results


def main():
    # Run the tutorials
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_flip_biased_coin())
    # loop.run_until_complete(tutorial_2())


if __name__ == "__main__":
    main()
    print("Tutorial 1 ran successfully")