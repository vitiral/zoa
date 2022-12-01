#include "civ/civ_unix.h"
#include "./zoa.h"

TEST(u4)
  U1 dat[10];
  Ring r = Ring_init(dat, 10);
  zoab_txU4(&r, 0xFedCab);
  TASSERT_EQ(3, dat[0]);
  TASSERT_EQ(0xFe, dat[1]); TASSERT_EQ(0xdC, dat[2]); TASSERT_EQ(0xab, dat[3]);

  TASSERT_EQ(0xFedCab, zoab_rxU4(&r));
  Ring_extend(&r, Slc_ntLit("\x01\xF3"));
  TASSERT_EQ(0xF3, zoab_rxU4(&r));
END_TEST

int main() {
  eprintf("# Running tests:\n");
  test_u4();
  return 0;
}
