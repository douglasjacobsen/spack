# Copyright 2013-2024 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import spack.util.path
import spack.paths


def get_projection(projections, spec):
    """
    Get the projection for a spec from a projections dict.
    """
    all_projection = None
    for spec_like, projection in projections.items():
        if spec.satisfies(spec_like):
            return spack.util.path.substitute_path_variables(
                projection, replacements=spack.paths.path_replacements()
            )
        elif spec_like == "all":
            all_projection = spack.util.path.substitute_path_variables(
                projection, replacements=spack.paths.path_replacements()
            )
    return all_projection
