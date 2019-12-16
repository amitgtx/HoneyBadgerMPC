'''
This implementation is a PoC to demonstrate how a MPC-firendly PRF 
can be used for realizing the "Proof of Custody" scheme. In short, 
Proof of Custody is a way for nodes (called validators) to "prove" 
that they are really storing a file which they are obligated to 
store. Prior realizations of this scheme utilized a "mix" function 
based on SHA256. Future goal is to make use of primitives which 
allow: i) validator pools to be set up in a secure, trustless manner, 
(ii) allow one-party validators to spread their secret across several 
machines, reducing the risk of secrets getting compromised. In order 
to meet this goal, it is required that the primitive is MPC-friendly 
which, unfortunately, is not a property of SHA256. Fortunately, the 
"mix" function in the Proof of CUstody scheme can be replaced with 
any PRF. Consequently, it was proposed that Legendre PRF, an 
MPC-friendly primitive, would be a good candidate for such replacement
(https://ethresear.ch/t/using-the-legendre-symbol-as-a-prf-for-the-proof-of-custody/5169)

The setting is such that there are n nodes out of which t might be 
malicious. There is a secret-key K which is secret-shared among the n 
nodes using a (t, n) threshold secret-sharing scheme. This means that 
atleast a group of t+1 nodes are required in-order to reconstruct the 
secret-key K. In order to "prove the custody" of set of B blocks 
- {X1, X2, .... XB} - which is basically a public dataset of B field 
elements, the nodes compute the output of legendre PRF function using 
their secret key share [k] and the B field elements as input. This 
output is represented in the following equation:
    

F_[k](X) = legendre_p(([k]+X1) * ([k]+X2) * ([k]+X3)  .... ([k]+XB))


Once each node has computed its share of the output, those outputs 
can be combined to reconstruct the actual output. In a setting where 
n > 3t, we can use a technique called robust interpolation for such 
reconstruction. This technique ensures that: i) reconstructed output 
always matches with the expected output, ii) nodes which did not 
submit or submitted incorrect shares of their PRF output are always 
identified. This identification of malicious behaviour (coupled with 
a scheme which provides rewards to nodes who submit correct output 
shares) incentivizes the nodes to perform the MPC computation honestly.


Below, we outline the protocol that each node follows:

Precompute:
-  [k],[k^2],...[k^B] ; powers of k (secret-share of key) for each 
block

Online computation:
- Compute [y] where y = (k+X1)(k+X2)....(k+XB) through local 
computations. This is a polynomial y = f(k) where the coefficients of 
f can be determined from constants X1,...,XB, and we have powers of 
[k] precomputed
- Compute [F_k(X)] := [y]^((p-1)/2) through log2 p multiply/squarings
- Open F_k(X) and reconstruct


In the following code, the above protocol is implemented inside the 
prog() function in 2 different phases:

- Offline Phase : In this phase, each node obtains a (t,n)
secret-sharing of random key K, and then each node computes succesive
powers of their secret share ([k], [k^2], [k^3], etc) using the
offline_powers_generation() function

- Online Phase : In this phase, nodes run a MPC protocol using the 
public file (represented as an array X of B elements) and the 
preprocessed powers of secret shared key as input. The logic for same 
is present in the eval() function. The output of this function is a 
secret-sharing fk_x of the desired output. After this, each node 
reconstructs the desired output FK_x using the open() function.


This implementation differs from a real-world deployment in the
following ways:

1.) The nodes in this demo are "simulated" as async tasks
which execute concurrently on the same system and communicate with
each other using message passing. However, in the real-world, each
node would correspond to a validator (a standalone system) and the
communication would happen over network sockets

2.) In this demo, nodes obtain a share of the predetermined 
secret-key K which is computed by the honeybadgerMPC system. In the 
real world, the "one-party validator" node will be holding the 
secret-key K and will be responsible for distributing shares of it to 
each of the n nodes in the "validator pool"
'''



import asyncio
import random
import time
# import sys
from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.field import GF
from honeybadgermpc.elliptic_curve import Subgroup
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
from honeybadgermpc import polynomial

config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply()
}

FIELD = GF(Subgroup.BLS12_381)
POLY = polynomial.polynomials_over(FIELD)

# Sampling a uniformly random Secret key
K = FIELD.random()

# Initializing the number of file blocks
B = random.randint(1, 100)

# Sampling B uniformly random field elements to be used as blocks
X = [FIELD.random() for _ in range(B)]  

# Create a test network of 4 nodes (no sockets, just asyncio tasks)
n, t = 4, 1

tBegin = time.time()

pp = FakePreProcessedElements()

# Generating Beaver triples
pp.generate_triples(B + 512, n, t)

print ((B + 512), "Triples generated ", time.time() - tBegin)

# Generating secret shares of key K 
sid = pp.generate_share(n, t, K)


# Compute [F_K(X)] := [y]^((p-1)/2) through log2 p multiply/squarings
def prf(ctx, y: Share):
    
    p = ctx.field.modulus
    exponent =  int ((p - 1) / 2)
    res = ctx.ShareFuture()
    res.set_result(ctx.Share(1))

    while exponent > 0:
        if(exponent & 1):
            res = res * y
        y = y * y
        exponent = exponent >> 1

    return res


# Offline phase for generating secret-shared powers of K
def offline_powers_generation(ctx, k: Share, powers):

    # Precompute [K],[K^2],...[K^B]   powers of k for each block
    powers_of_k_shares = []
    ith_power_share = ctx.Share(1)

    for i in range(powers):
        ith_power_share = ith_power_share * k
        powers_of_k_shares.append(ith_power_share)

    return powers_of_k_shares


# # Compute coeffecient of the polynomial (K - X1)(K - X2).....(K - XB)
def find_coeff_from_roots(roots):
	
	degree = len(roots)

	if(degree == 1):
		return POLY([roots[0], 1])

	# print (int(degree/2))
	p1 = find_coeff_from_roots(roots[:int(degree/2)])
	p2 = find_coeff_from_roots(roots[int(degree/2):])

	n = 1 << degree.bit_length()

	omega = polynomial.get_omega(FIELD, n)

	y1 = p1.evaluate_fft(omega, n)
	y2 = p2.evaluate_fft(omega, n)

	y = [y1[i] * y2[i] for i in range(n)]


	y3 = POLY.interpolate_fft(y, omega)

	return y3




# Evaluting the prf on a fixed number of field elements X 
# using precomputed secret-shared powers of K 
async def eval(ctx, powers_of_k_shares, X):

    poly = find_coeff_from_roots(X)
    coeff = poly.coeffs


    # Compute [y] where y = (K+X1)(K+X2)....(K+XB) through local computations
    # This is a polynomial y = f(K) where the coefficients of f have been stored in `coeff`, and we have powers of [k] precomputed
    y = coeff[0]   

    for i in range(B):
        y = y + powers_of_k_shares[i] * coeff[1 + i]


    fk_x = await prf(ctx, y)
    print(f"[{ctx.myid}] PRF OK")
    
    return fk_x


# Verify whether the reconstrcuted MPC result matches the expected
# result F_K(X) = legendre_p( (K+X1) * (K+X2) * (K+X3)  .... (K+XB)) 
def verify(mpcResult, K, X):

    p = FIELD.modulus
    Y = FIELD(1)

    #Calculating Y = (K + X1) * (K + X2) ...... * (K + XB)
    for Xi in X:
        Y *= (K + Xi)

    
    #Calculating expectedResult = legendre_p(Y)
    expectedResult = FIELD(1)
    exponent = int((p - 1) / 2)

    while exponent > 0:
        if(exponent & 1):
            expectedResult *= Y
        Y = Y * Y
        exponent = exponent >> 1

    return mpcResult == expectedResult



async def prog(ctx):


    #############################################
    ############## OFFLINE PHASE ################
    #############################################

    # Fetching a share of secret key
    k = ctx.preproc.get_share(ctx, sid)
    

    tBegin = time.time()
    # Powers of [K] ([K]^1, [K]^2, .... [K]^B) which we wish to precompute
    powers_of_k_shares = offline_powers_generation(ctx, k, B)

    await asyncio.gather(*powers_of_k_shares)

    print(f"[{ctx.myid}] Offline Power Generation OK", time.time() - tBegin)

    # offline_openings = ctx.opening_count
    # print(f"[{ctx.myid}] Offline Opening Count: ", offline_openings)



    #############################################
    ############### ONLINE PHASE ################
    #############################################


    # Evaluating the legendre PRF on elements in public list X
    tBegin = time.time()
    fk_x = await eval(ctx, powers_of_k_shares, X)
    print(f"[{ctx.myid}] Legendre PRF Evaluation OK", time.time() - tBegin)


    # Open F_k(X) and reconstruct
    tBegin = time.time()
    FK_x = await fk_x.open()
    print(f"[{ctx.myid}] Output share reconstruction OK: ", FK_x, time.time() - tBegin)

    # online_openings = ctx.opening_count - offline_openings
    # print(f"[{ctx.myid}] Opening Count: ", online_openings)

    # Return the reconstructed value
    return FK_x


async def legendrePRF_proofOfCustody():
    
    program_runner = TaskProgramRunner(n, t, config)
    program_runner.add(prog)
    results = await program_runner.join()

    # Verifying whether reconstructed output matches with the expected output
    assert len(results) == n
    for result in results:
        assert verify(result, K, X) == True

    return results


def main():

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(legendrePRF_proofOfCustody())


if __name__ == "__main__":
    main()
    print("Legendre PRF based Proof of Custody scheme ran successfully", B, n, t)