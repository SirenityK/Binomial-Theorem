from math import factorial

# Makes a number superscript
def gs(x):
    normal = "0123456789-"
    super_s = "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"
    res = x.maketrans(''.join(normal), ''.join(super_s))
    return x.translate(res)

# Returns an integer number if it is integer. This fixes a printed number with unnecessary decimal point --> x.0
def fn(num): return int(num) if num%1==0 else num

# Binomial Coefficient
def nCr(n1,n2): return fn(factorial(n1)/(factorial(n2)*factorial(n1-n2)))

# Removes unnecessary multipliers
def simp(x):
    if x==0 or x==1 or x=='1' or x=='0' or x==-1 or x=='-1': return '' if x!=-1 else '-'
    else: return str(x)

# a = True; boolean value
a = 1
while a:
    print('(a+b)ⁿ')
    x,y,n=input("Enter 'a' multiplier: "),input("Enter 'b' multiplier: "),input("Enter n: ")
    try:
        x,y,n=fn(float(x)),fn(float(y)),int(n)

        # Prints equation depending of introduced values
        if x!=0 or y!=0 and n>0: print('\n({}{}){}'.format(simp(fn(x))+'a' if x!=0 else '',('+' if y>0 and x!=0 else '')+simp(fn(y))+('b' if y!=0 else ''),gs(str(n))),end=' = ')
        elif x==0 and y==0 and n!=0: print('0'+gs(simp(str(n))),end=' = ')
        elif n<0: pass
        else: print('\n0'+gs('0'),end=' = ')
        if n>=1030: print("Error.\n'n' must be less than 1030.")
        elif n>0 and n!=1 and x!=0 and y!=0:

            # Binomial Theorem
            for k in range(0,n+1):
                nk=nCr(n,k)
                x1=x**(n-k)
                y1=y**k
                if k==0: print('{}a{}'.format(simp(round(fn(nk*x1*y1),5)),gs(str(n))),end='')
                elif k<=n-1: print('{}a{}b{}'.format(('+' if nk*x1*y1>0 else '')+str(simp(round(fn(nk*x1*y1),5))),gs(simp(str(n-k))),gs(simp(str(k)))),end='')
                else: print('{}b{}'.format(('+' if y1>0 else '')+simp(round(fn(y1),5)),gs(str(n))))

        # Different outputs depending in what is introduced
        elif n==0 and x==0 and y==0: print('Undefined')
        elif n!=0 and x==0 and y==0: print(0)
        elif x!=0 and y!=0 and n==0: print('1,{0}{1} ≠ 0; case {0}{1} = 0, Undefined'.format(simp(fn(x))+'a' if x!=0 else '',('+' if y>0 and x!=0 else '')+simp(fn(y))+('b' if y!=0 else '')))
        elif n==1: print('{}{}'.format(simp(fn(x))+'a' if x!=0 else '',('+' if y>0 and x!=0 else '')+simp(fn(y))+('b' if y!=0 else '')))
        elif n<0: print("Error. 'n' can't be less than 0.")
        else: print('{}{}'.format(simp(fn(x**n))+('a'+gs(str(n))) if x!=0 else '',simp(fn(y**n))+('b'+gs(str(n))) if y!=0 else ''))

    # Bug and bad input fixes
    except ValueError: print("\nInput error. Introduce numbers. Integer for 'n'.")
    except OverflowError: print('Error. Too large numbers in output.')

    # Repeating system
    a = input('\ny/n for repeat or quit program: ').lower()
    if a=='n': a = False
    elif a!='y':
        a = False
        print('Stopping due to no certain answer..')
    else: print('')