'''
This implementation is a PoC to demonstrate how an MPC-firendly PRF 
can be used for realizing the "Proof of Custody" scheme. In short, 
Proof of Custody is a way for nodes (called validators) to "prove" 
that they are really storing a file which they are obligated to 
store. Prior realizations of this scheme utilized a "mix" function 
based on SHA256. Future goal is to make use of primitives which allow 
i) validator pools to be set up in a secure, trustless manner and 
(ii) allow one-party validators to spread their secret across several 
machines, reducing the risk of secrets getting compromised. In order 
to meet this goal, it is required that the primitive is MPC-friendly 
which, unfortunately, is not a property of SHA256. Fortunately, the 
"mix" function in the Proof of CUstody scheme can be replaced with 
any PRF. Consequently, it was proposed that Legendre PRF, an 
MPC-friendly primitive, would be a good candidate for such 
replacement
(https://ethresear.ch/t/using-the-legendre-symbol-as-a-prf-for-the-proof-of-custody/5169)

The setting is such that there are n nodes out of which t might be 
malicious. There is a secret-key K which is secret-shared among the n 
nodes using a (t, n) threshold secret-sharing scheme. This means that 
atleast a group of t+1 nodes are required in-order to reconstruct the 
secret-key K. In order to "prove the custody" of set of B blocks 
- {X1, X2, .... XB} - which is basically a public dataset of B field 
elements, the nodes compute the output of legendre PRF function using 
their secret key-share [k] and the B field elements as input. This 
output is represented in the following equation:
    

F_[k](X) = legendre_p(([k]+X1) * ([k]+X2) * ([k]+X3)  .... ([k]+XB))


Once each node has computed its share of the output, those outputs 
can be combined in-order to reconstruct the actual output. In a 
setting where n > 3t, we can use a technique called robust 
interpolation for such reconstruction. This technique ensures that 
i)reconstructed output always matches with the expected output 
ii) nodes which did not submit or submitted incorrect shares of their 
PRF output are always identified. This identification of malicious 
behaviour (coupled with a scheme which provides rewards to nodes 
submitting correct output shares) incentivizes the nodes to perform 
the MPC computation honestly.


Below, we outline the protocol that each node follows:

Precompute:
-  [k],[k^2],...[k^B]   powers of k for each block

Protocol:
- Compute [y] where y = (k+X1)(k+X2)....(k+XB) through Local 
computations. This is a polynomial y = f(k) where the coefficients of 
f can be determined from constants X1,...,XB, and we have powers of 
[k] precomputed
- Compute [F_k(X)] := [y]^((p-1)/2) through log2 p multiply/squarings
- Open F_k(X) and reconstruct


The above protocol is implemented inside the prog() function in 2
 different phases:

- Offline Phase : In this phase, all nodes collectively obtain a (t,n)
secret-sharing of random key K, and then each node computes succesive
powers of their secret share ([k], [k^2], [k^3], etc) using the
offline_powers_generation() function

- Online Phase : In this phase, nodes receive a file (represented as
an array X of B elements) as input, and then run the MPC protocol by
consuming the preprocessed powers to obtain a secret-sharing fk_x of
the desired output. The logic for same is present in the eval()
function. After this, each node reconstructs the desired output FK_x
using the open() function.


This implementation differs from a real-world deployment in the
following way: The nodes in this demo are "simulated" as async tasks
which execute concurrently on the same system and communicate with
each other using message passing. However, in the real-world, each
node would correspond to a validator (a standalone system) and the
communication would happen over network sockets

'''



import asyncio
import random
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

config = {
    MixinConstants.MultiplyShareArray: BeaverMultiplyArrays(),
    MixinConstants.MultiplyShare: BeaverMultiply()
}

FIELD = GF(Subgroup.BLS12_381)

# Sampling a uniformly random Secret key
K = FIELD.random()

# Initializing the number of file blocks
B = random.randint(1, 100)

# Sampling B uniformly random field elements to be used as blocks
X = [FIELD.random() for _ in range(B)]  

# Create a test network of 4 nodes (no sockets, just asyncio tasks)
n, t = 4, 1

pp = FakePreProcessedElements()

# Generating secret sharings of 0
pp.generate_zeros(10000, n, t)

# Generating Beaver triples
pp.generate_triples(10000, n, t)

# Generating secret shares of key K 
sid = pp.generate_share(n, t, K)



# Compute [F_K(X)] := [y]^((p-1)/2) through log2 p multiply/squarings
async def prf(ctx, y: Share):
    
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


# Evaluting the prf on a fixed number of field elements X 
# using precomputed secret-shared powers of K 
async def eval(ctx, powers_of_k_shares, X):
    

    # Determing coefficients of (K + X1)(K + X2).....(K + XB)
    coeff = [ctx.field(1)]

    for Xi in X:
        shift_coeff = coeff + [ctx.field(0)]
        mult_coeff = [ctx.field(0)] + [elem * Xi for elem in coeff]
        coeff = [i + j for i, j in zip(shift_coeff, mult_coeff)]


    # Compute [y] where y = (K+X1)(K+X2)....(K+XB) through Local computations
    # This is a polynomial y = f(K) where the coefficients of f have been stored in `coeff`, and we have powers of [k] precomputed
    y = coeff[B]   

    for i in range(B):
        y = y + powers_of_k_shares[i] * coeff[B - 1 - i]


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
    
    # Powers of [K] ([K]^1, [K]^2, .... [K]^B) which we wish to precompute
    powers_of_k_shares = offline_powers_generation(ctx, k, B)
    print(f"[{ctx.myid}] Offline Power Generation OK")



    #############################################
    ############### ONLINE PHASE ################
    #############################################


    # Evaluating the legendre PRF on elements in public list X
    fk_x = await eval(ctx, powers_of_k_shares, X)
    print(f"[{ctx.myid}] Legendre PRF Evaluation OK")


    # Open F_k(X) and reconstruct
    FK_x = await fk_x.open()
    print(f"[{ctx.myid}] Output share reconstruction OK")


    # Return the reconstructed value
    return FK_x


async def legendrePRF_challenge():
    
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
    loop.run_until_complete(legendrePRF_challenge())


if __name__ == "__main__":
    main()
    print("Legendre PRF based Proof of Custody scheme ran successfully")