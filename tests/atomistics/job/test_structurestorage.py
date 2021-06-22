from pyiron_atomistics._tests import TestWithProject
from pyiron_contrib.atomistics.atomistics.job.structurestorage import StructureStorage
import os.path
import numpy as np

class TestContainer(TestWithProject):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.elements = ("Fe", "Mg", "Al", "Cu", "Ti")
        cls.structures = [cls.project.create.structure.bulk(el).repeat(3) for el in cls.elements]

    def setUp(self):
        self.cont = StructureStorage(
                    num_structures=len(self.structures),
                    num_atoms=sum(len(s) for s in self.structures)
        )
        for s in self.structures:
            self.cont.add_structure(s, s.get_chemical_formula())

    def tearDown(self):
        del self.cont

    def test_len(self):
        """Length of container should be equal to number of calls to add_structure."""
        self.assertEqual(len(self.cont), len(self.structures))

    def test_get_elements(self):
        """get_elements() should return all unique chemical elements stored in its structures."""
        self.assertEqual(sorted(self.elements), sorted(self.cont.get_elements()),
                         "Results from get_elements() do not match added elements.")

    def test_add_array(self):
        """Custom arrays added with add_array should be properly allocated with matching shape, dtype and fill"""

        self.cont.add_array("energy", per="structure")
        self.cont.add_array("forces", shape=(3,), per="atom")
        self.cont.add_array("fnorble", shape=(), dtype=np.int64, fill=0, per="atom")

        self.assertTrue("energy" in self.cont._per_structure_arrays,
                        "no 'energy' array present after adding it with add_array()")
        self.assertEqual(self.cont._per_structure_arrays["energy"].shape, (self.cont._num_structures_alloc,),
                        "'energy' array has wrong shape")

        self.assertTrue("forces" in self.cont._per_atom_arrays,
                        "no 'forces' array present after adding it with add_array()")
        self.assertEqual(self.cont._per_atom_arrays["forces"].shape, (self.cont._num_atoms_alloc, 3),
                        "'forces' array has wrong shape")

        self.assertEqual(self.cont._per_atom_arrays["fnorble"].dtype, np.int64,
                         "'fnorble' array has wrong dtype after adding it with add_array()")
        self.assertTrue((self.cont._per_atom_arrays["fnorble"] == 0).all(),
                         "'fnorble' array not initialized with given fill value")

        self.cont.add_array("fnorble", shape=(), dtype=np.int64, fill=42, per="atom")
        self.assertTrue(not (self.cont._per_atom_arrays["fnorble"] == 42).all(),
                         "Duplicate add_array call was not ignored")

        self.cont.add_array("energy", fill=42, per="structure")
        self.assertTrue(not (self.cont._per_structure_arrays["energy"] == 42).all(),
                         "Duplicate add_array call was not ignored")

    def test_get_array(self):
        """get_array should return the arrays for the correct structures."""

        for i, structure in enumerate(self.structures):
            self.assertTrue(np.allclose(self.cont.get_array("positions", i), structure.positions),
                            f"get_array returns wrong positions for structure {i}")
            self.assertTrue(np.allclose(self.cont.get_array("cell", i), structure.cell.array),
                            f"get_array returns wrong positions for structure {i}")

    def test_set_array(self):
        """set_array should set the arrays for the correct structures and only those."""

        new_pbc = [True, False, True]
        self.cont.set_array("pbc", 0, new_pbc)
        self.assertTrue((self.cont.get_array("pbc", 0,) == new_pbc).all(),
                        f"Value from get_array {self.cont.get_array('pbc', 0)} does not match set value {new_pbc}")

        symbols = self.cont.get_array("symbols", 2)
        symbols[5:10] = 'Cu'
        self.cont.set_array("symbols", 2, symbols)
        self.assertTrue((self.cont.get_array("symbols", 2) == symbols).all(),
                        f"Value from get_array {self.cont.get_array('symbols', 0)} does not match set value {symbols}")

        self.cont.set_array("positions", 0, np.ones( (len(self.structures[0]), 3) ))
        for i, structure in enumerate(self.structures):
            if i == 0: continue

            self.assertTrue(np.allclose(self.cont.get_array("positions", i), structure.positions),
                            f"set_array modified arrray for different structure than instructured.")

    def test_has_array(self):
        """hasarray should return correct information for added array; None otherwise."""

        pbc = self.cont.has_array("pbc")
        self.assertEqual(pbc["dtype"], bool, "has_array returns wrong dtype for per structure array.")
        self.assertEqual(pbc["shape"], (3,), "has_array returns wrong shape for per structure array.")
        self.assertEqual(pbc["per"], "structure", "has_array returns wrong per for per structure array.")

        pbc = self.cont.has_array("positions")
        self.assertEqual(pbc["dtype"], np.float64, "has_array returns wrong dtype for per atom array.")
        self.assertEqual(pbc["shape"], (3,), "has_array returns wrong shape for per atom array.")
        self.assertEqual(pbc["per"], "atom", "has_array returns wrong per for per atom array.")

        self.assertEqual(self.cont.has_array("missing"), None, "has_array does not return None for nonexisting array.")

    def test_get_structure(self):
        """Structure from get_structure should match thoes add with add_structure exactly."""

        for i, s in enumerate(self.structures):
            self.assertEqual(s, self.cont.get_structure(i),
                             "Added structure not equal to returned structure.")

    def test_translate_frame(self):
        """Using get_structure with the given identifiers should return the respective structure."""
        for s in self.structures:
            self.assertEqual(s, self.cont.get_structure(s.get_chemical_formula()),
                             "get_structure returned wrong structure for given identifier.")

    def test_add_structure(self):
        """add_structure(identifier=None) should set the current structure index as identifier"""

        for i, structure in enumerate(self.structures):
            self.cont.add_structure(structure)
            self.assertEqual(self.cont.get_array("identifier", len(self.structures) + i),
                             str(len(self.structures) + i),
                             "Default identifier is incorrect.")

    def test_add_structure_kwargs(self):
        """Additional kwargs given to add_structure should create appropriate custom arrays."""

        E = 3.14
        P = np.eye(3) * 2.72
        F = np.array([[1,3,5]] * len(self.structures[0]))
        R = np.ones(len(self.structures[0]))
        self.cont.add_structure(self.structures[0], self.structures[0].get_chemical_formula(),
                                energy=E, forces=F, pressure=P, fnord=R[None, :])
        self.assertEqual(self.cont.get_array("energy", self.cont.num_structures - 1), E,
                         "Energy returned from get_array() does not match energy passed to add_structure")
        got_F = self.cont.get_array("forces", self.cont.num_structures - 1)
        self.assertTrue(np.allclose(got_F, F),
                        f"Forces returned from get_array() {got_F} do not match forces passed to add_structure {F}")
        got_P = self.cont.get_array("pressure", self.cont.num_structures - 1)
        self.assertTrue(np.allclose(got_P, P),
                        f"Pressure returned from get_array() {got_P} does not match pressure passed to add_structure {P}")
        self.assertTrue("fnord" in self.cont._per_structure_arrays,
                        "array 'fnord' not in per structure array, even though shape[0]==1")
        got_R = self.cont.get_array("fnord", self.cont.num_structures - 1)
        self.assertEqual(got_R.shape, R.shape,
                        f"array 'fnord' added with wrong shape {got_R.shape}, even though shape[0]==1 ({R.shape})")
        self.assertTrue((got_R == R).all(),
                        f"Fnord returned from get_array() {got_R} does not match fnord passed to add_structure {R}")

    def test_add_structure_spins(self):
        """If saved structures have spins, they should be saved and restored, too."""

        fe = self.structures[0].copy()

        cont = StructureStorage()
        spins = [1] * len(fe)
        fe.set_initial_magnetic_moments(spins)
        cont.add_structure(fe, "iron_spins")
        fe_read = cont.get_structure("iron_spins")
        self.assertTrue(fe_read.spins is not None,
                        "Spins not restored on added structure.")
        self.assertTrue(np.allclose(spins, fe_read.spins),
                        f"Spins restored on added structure not equal to original spins: {spins} {fe_read.spins}.")

        # repeat for vector spins
        cont = StructureStorage()
        spins = [(1,0,1)] * len(fe)
        fe.set_initial_magnetic_moments(spins)
        cont.add_structure(fe, "iron_spins")
        fe_read = cont.get_structure("iron_spins")
        self.assertTrue(fe_read.spins is not None,
                        "Spins not restored on added structure.")
        self.assertTrue(np.allclose(spins, fe_read.spins),
                        f"Spins restored on added structure not equal to original spins: {spins} {fe_read.spins}.")

    def test_resize(self):
        """A dynamically resized container should behave exactly as a pre-allocated container."""

        cont_static = self.cont
        cont_dynamic = StructureStorage(num_structures=2, num_atoms=10)

        for s in self.structures:
            cont_dynamic.add_structure(s, s.get_chemical_formula())

        self.assertEqual(cont_static.current_atom_index, cont_dynamic.current_atom_index,
                         "Dynamic container doesn't have the same current atom after adding structures.")
        self.assertEqual(cont_static.current_structure_index, cont_dynamic.current_structure_index,
                         "Dynamic container doesn't have the same current structure after adding structures.")
        self.assertTrue( (cont_static.symbols[:cont_static.current_atom_index] \
                            == cont_dynamic.symbols[:cont_dynamic.current_atom_index]).all(),
                        "Array of chemical symbols not equal after adding structures.")
        self.assertTrue(np.isclose(cont_static.positions[:cont_static.current_atom_index],
                                   cont_static.positions[:cont_dynamic.current_atom_index]).all(),
                        "Array of chemical symbols not equal after adding structures.")
        self.assertTrue(np.isclose(cont_static.cell[:cont_static.current_structure_index],
                                   cont_dynamic.cell[:cont_dynamic.current_structure_index]).all(),
                        "Array of chemical symbols not equal after adding structures.")
        self.assertTrue( (cont_static.identifier[:cont_static.current_structure_index] \
                            == cont_dynamic.identifier[:cont_dynamic.current_structure_index]).all(),
                        "Array of chemical symbols not equal after adding structures.")

    def test_hdf(self):
        """Containers written to, then read from HDF should match."""
        hdf = self.project.create_hdf(self.project.path, "test_hdf")
        self.cont.to_hdf(hdf)
        cont_read = StructureStorage()
        cont_read.from_hdf(hdf)

        self.assertEqual(len(self.cont), len(cont_read), "Container size not matching after reading from HDF.")
        self.assertEqual(self.cont.num_structures, cont_read.num_structures,
                         "num_structures does not match after reading from HDF.")
        self.assertEqual(self.cont.num_atoms, cont_read.num_atoms,
                         "num_atoms does not match after reading from HDF.")
        for s1, s2 in zip(self.cont.iter_structures(), cont_read.iter_structures()):
            self.assertEqual(s1, s2, "Structure from get_structure not matching after reading from HDF.")

        cont_read.to_hdf(hdf, "other_structures")
        cont_read.from_hdf(hdf, "other_structures")

        # bug regression: if you mess up reading some variables it might work fine when you use but it could write
        # itself wrongly to the HDF, thus double check here.
        self.assertEqual(len(self.cont), len(cont_read), "Container size not matching after reading from HDF twice.")
        self.assertEqual(self.cont.num_structures, cont_read.num_structures,
                         "num_structures does not match after reading from HDF twice.")
        self.assertEqual(self.cont.num_atoms, cont_read.num_atoms,
                         "num_atoms does not match after reading from HDF twice.")
        for s1, s2 in zip(self.cont.iter_structures(), cont_read.iter_structures()):
            self.assertEqual(s1, s2, "Structure from get_structure not matching after reading from HDF twice.")