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
from honeybadgermpc.progs.fixedpoint import FixedPoint

from honeybadgermpc.progs.mixins.share_comparison import MixinConstants, Equality, LessThan


config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply(),
    MixinConstants.ShareLessThan: LessThan(),
    MixinConstants.ShareEquality: Equality()
}
# import numpy as np


def create_secret_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(x * 2 ** 32) + ctx.preproc.get_zero(ctx))

def create_clear_share(ctx, x):
    return FixedPoint(ctx, ctx.Share(int(x * 2 ** 32)))   


def convert_integer_ss_to_fixed_point_ss(ctx, integer_ss):

	scaled_integer_ss = integer_ss * 2 ** 32

	return FixedPoint(ctx, scaled_integer_ss)



### WORK IN PROGRESS ######

# async def flip_biased_coin(ctx, heads_weight, tails_weight):

# 	total_weight = heads_weight + tails_weight

# 	# normalized_weight = 

# 	# Flipping a 20 bit fair coin  
# 	coin = ctx.Share(0)
# 	bits = 8

# 	for i in range(bits):

# 		coin += 2**i * ctx.preproc.get_bit(ctx)


# 	normalized_coin = await convert_integer_ss_to_fixed_point_ss(ctx, coin).div(2 ** bits)

# 	return coin, normalized_coin



# Assumption - tails_weight is a 8 bit value (will be instantiated using some mom's gene attribute)
async def flip_biased_coin(ctx, tails_weight):

	bits = 8

	# Normalizing tails_weight to a real value in [0, 1]
	normalized_tails_weight = await convert_integer_ss_to_fixed_point_ss(ctx, tails_weight).div(2 ** bits)

	# Flipping a 8 bit fair coin  
	coin = ctx.Share(0)

	for i in range(bits):

		coin += 2**i * ctx.preproc.get_bit(ctx)

	# Normalizing coin value to a real value in [0, 1]
	normalized_coin = await convert_integer_ss_to_fixed_point_ss(ctx, coin).div(2 ** bits)

	result = await normalized_coin.lt(normalized_tails_weight)

	return result



async def prog(ctx):

	# Number of biased coins that need to be flipped
	N = 10

	# Intializing Dad's and Mom's secret gene as some arbitrary numbers 
	# dad = 100
	mom = 128

	for i in range(N):

		# Secret share of Dad's and Mom's gene
		# dad_ss = ctx.Share(dad) + ctx.preproc.get_zero(ctx)
		mom_ss = ctx.Share(mom) + ctx.preproc.get_zero(ctx)


		# Flipping a biased coin whose Head weight is depends on Dad'd gene whereas Tails weight depends on Mom's gene
		# res_ss = await flip_biased_coin(ctx, dad_ss, mom_ss)
		# coin_ss, normalized_coin_ss = await flip_biased_coin(ctx, dad_ss, mom_ss)

	
		coin_ss = await flip_biased_coin(ctx, mom_ss)

		# Opening the output
		# res = await res_ss.open()
		coin = await coin_ss.open()
		# normalized_coin = await normalized_coin_ss.open()

		print(f"[{ctx.myid}] Biased coin {i}: {coin}")
		# print(f"[{ctx.myid}] Biased bit {i}: {coin, normalized_coin}")




async def test_flip_biased_coin():
    # Create a test network of 4 nodes (no sockets, just asyncio tasks)
    n, t = 4, 1
    pp = FakePreProcessedElements()
    pp.generate_zeros(10000, n, t)
    pp.generate_triples(10000, n, t)
    pp.generate_rands(10000, n, t)
    pp.generate_bits(10000, n, t)
    pp.generate_share_bits(100, n, t)
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