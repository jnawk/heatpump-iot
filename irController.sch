v 20130925 2
C 40000 40000 0 0 0 title-B.sym
C 43600 49800 1 0 0 5V-plus-1.sym
C 43000 42600 1 0 0 3.3V-plus-1.sym
C 43700 45800 1 0 0 led-1.sym
{
T 44500 46400 5 10 0 1 0 0 1
device=LED
T 43600 45600 5 10 1 1 0 0 1
refdes=1.6V 1000mA max
T 44500 46600 5 10 0 1 0 0 1
symversion=0.1
}
C 46800 45800 1 0 0 led-1.sym
{
T 47600 46400 5 10 0 0 0 0 1
device=LED
T 46600 45600 5 10 1 1 0 0 1
refdes=1.6V 1000mA max
T 47600 46600 5 10 0 0 0 0 1
symversion=0.1
}
C 46700 49300 1 0 0 resistor-1.sym
{
T 47000 49700 5 10 0 0 0 0 1
device=RESISTOR
T 46900 49000 5 10 1 1 0 0 1
refdes=10k
}
C 45300 45900 1 0 0 resistor-1.sym
{
T 45600 46300 5 10 0 0 0 0 1
device=RESISTOR
T 45500 46200 5 10 1 1 0 0 1
refdes=1 ohm
}
C 48500 45900 1 0 0 resistor-1.sym
{
T 48800 46300 5 10 0 0 0 0 1
device=RESISTOR
T 48700 46200 5 10 1 1 0 0 1
refdes=1 ohm
}
C 48600 45000 1 0 0 resistor-1.sym
{
T 48900 45400 5 10 0 0 0 0 1
device=RESISTOR
T 48800 45300 5 10 1 1 0 0 1
refdes=10k
}
C 50100 44600 1 0 0 2N2222-1.sym
{
T 51000 45300 5 10 0 0 0 0 1
device=2N2222
T 51000 45100 5 10 1 1 0 0 1
refdes=Q?
}
C 51400 48200 1 0 0 connector4-2.sym
{
T 52100 50300 5 10 1 1 0 6 1
refdes=DHT22
T 51700 50250 5 10 0 0 0 0 1
device=CONNECTOR_4
T 51700 50450 5 10 0 0 0 0 1
footprint=SIP4N
}
N 43800 49800 51400 49800 4
C 49500 48300 1 0 0 out-1.sym
{
T 49500 48600 5 10 0 0 0 0 1
device=OUTPUT
T 49500 48600 5 10 1 1 0 0 1
refdes=GPIO #22
}
C 44400 41300 1 0 0 out-1.sym
{
T 44400 41600 5 10 0 0 0 0 1
device=OUTPUT
T 44400 41000 5 10 1 1 0 0 1
refdes=GPIO #4
}
C 48700 43400 1 0 0 in-1.sym
{
T 48700 43700 5 10 0 0 0 0 1
device=INPUT
T 48700 43700 5 10 1 1 0 0 1
refdes=GPIO #23
}
N 47600 49400 51400 49400 4
N 49500 48400 49500 49400 4
N 42600 49400 46700 49400 4
N 50700 45600 50700 46000 4
N 44600 46000 45300 46000 4
N 46200 46000 46800 46000 4
N 47700 46000 48500 46000 4
N 43200 42600 43200 42000 4
C 41500 41200 1 0 0 connector3-1.sym
{
T 43300 42100 5 10 0 0 0 0 1
device=CONNECTOR_3
T 41500 42300 5 10 1 1 0 0 1
value=TSOP1738
}
C 45600 41400 1 0 0 ground.sym
N 43200 41700 45800 41700 4
N 43200 41400 44400 41400 4
C 47900 44200 1 0 0 ground.sym
N 49500 45100 50100 45100 4
N 48600 45100 48100 45100 4
N 48100 45100 48100 44500 4
N 49400 46000 50700 46000 4
C 50600 46600 1 0 0 ground.sym
N 51400 48600 50800 48600 4
N 49800 45100 49800 43500 4
N 49800 43500 49300 43500 4
C 43500 47100 1 0 0 5V-plus-1.sym
N 43700 47100 43700 46000 4
C 50500 43700 1 0 0 ground.sym
N 50700 44600 50700 44000 4
C 50200 47200 1 0 0 2N2222-1.sym
{
T 51100 47900 5 10 0 0 0 0 1
device=2N2222
T 51100 47700 5 10 1 1 0 0 1
refdes=Q?
}
N 50800 48600 50800 48200 4
N 50800 47200 50800 46900 4
N 48600 47200 48600 47700 4
C 49000 47600 1 0 0 resistor-1.sym
{
T 49300 48000 5 10 0 0 0 0 1
device=RESISTOR
T 49300 47900 5 10 1 1 0 0 1
refdes=1k
}
C 42400 49800 1 0 0 3.3V-plus-1.sym
N 42600 49400 42600 49800 4
C 49300 46700 1 0 0 in-1.sym
{
T 49300 47000 5 10 0 0 0 0 1
device=INPUT
T 49300 47000 5 10 1 1 0 0 1
refdes=GPIO #18
}
N 49900 46800 49900 47700 4
C 48400 46900 1 0 0 ground.sym
N 49900 47700 50200 47700 4
N 48600 47700 49000 47700 4
