# RPMs are split as follows:
# * booth:
#   - envelope package serving as a syntactic shortcut to install
#     booth-site (with architecture reliably preserved)
# * booth-core:
#   - package serving as a base for booth-{arbitrator,site},
#     carrying also basic documentation, license, etc.
# * booth-arbitrator:
#   - package to be installed at a machine accessible within HA cluster(s),
#     but not (necessarily) a member of any, hence no dependency
#     on anything from cluster stack is required
# * booth-site:
#   - package to be installed at a cluster member node
#     (requires working cluster environment to be useful)
# * booth-test:
#   - files for testing booth
#
# TODO:
# wireshark-dissector.lua currently of no use (rhbz#1259623), but if/when
# this no longer persists, add -wireshark package (akin to libvirt-wireshark)

%bcond_with html_man
%bcond_with glue
%bcond_with run_build_tests
%bcond_without include_unit_test

# set following to the result of  `git describe --abbrev=128 $commit`
# This will be used to fill booth_ver, booth_numcomm and booth_sha1.
# It is important to keep abbrev to get full length sha1! When updating source use
# `spectool -g booth.spec` to download source.
%global git_describe_str v1.0-283-g9d4029aa14323a7f3b496215d25e40bd14f33632

# Set this to 1 when rebasing (changing git_describe_str) and increase otherwise
%global release 1

# Run shell script to parse git_describe str into version, numcomm and sha1 hash
%global booth_ver %(s=%{git_describe_str}; vver=${s%%%%-*}; echo ${vver:1})
%global booth_numcomm %(s=%{git_describe_str}; t=${s#*-}; echo ${t%%%%-*})
%global booth_sha1 %(s=%{git_describe_str}; t=${s##*-}; echo ${t:1})
%global booth_short_sha1 %(s=%{booth_sha1}; echo ${s:0:7})
%global booth_archive_name %{name}-%{booth_ver}-%{booth_numcomm}-%{booth_short_sha1}

## User and group to use for nonprivileged services (should be in sync with pacemaker)
%global uname hacluster
%global gname haclient

# Disable automatic compilation of Python files in extra directories
%global _python_bytecompile_extra 0

%global github_owner ClusterLabs

%{!?_pkgdocdir: %global _pkgdocdir %{_docdir}/%{name}}
# https://fedoraproject.org/wiki/EPEL:Packaging?rd=Packaging:EPEL#The_.25license_tag
%{!?_licensedir:%global license %doc}

%global test_path   %{_datadir}/booth/tests

Name:           booth
Version:        %{booth_ver}
Release:        %{booth_numcomm}.%{release}.%{booth_short_sha1}.git%{?dist}
Summary:        Ticket Manager for Multi-site Clusters
License:        GPLv2+
Url:            https://github.com/%{github_owner}/%{name}
Source0:        https://github.com/%{github_owner}/%{name}/archive/%{booth_short_sha1}/%{booth_archive_name}.tar.gz
Patch0:         rhel-specific-0001-config-Add-enable-authfile-option.patch

# direct build process dependencies
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  coreutils
BuildRequires:  make
## ./autogen.sh
BuildRequires:  /bin/sh
# general build dependencies
BuildRequires:  asciidoc
BuildRequires:  gcc
BuildRequires:  pkgconfig
# linking dependencies
BuildRequires:  libgcrypt-devel
BuildRequires:  libxml2-devel
## just for <pacemaker/crm/services.h> include
BuildRequires:  pacemaker-libs-devel
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  zlib-devel
## logging provider
BuildRequires:  pkgconfig(libqb)
## random2range provider
BuildRequires:  pkgconfig(glib-2.0)
## nametag provider
BuildRequires:  pkgconfig(libsystemd)
# check scriptlet (for hostname and killall respectively)
BuildRequires:  hostname psmisc
BuildRequires:  python3-devel
# For generating tests
BuildRequires:  sed
# spec file specifics
## for _unitdir, systemd_requires and specific scriptlet macros
BuildRequires:  systemd
## for autosetup
BuildRequires:  git
%if 0%{?with_run_build_tests}
# check scriptlet (for perl and netstat)
BuildRequires:  perl-interpreter net-tools
%endif

# this is for a composite-requiring-its-components arranged
# as an empty package (empty files section) requiring subpackages
# (_isa so as to preserve the architecture)
Requires:       %{name}-core%{?_isa}
Requires:       %{name}-site
%files
%license COPYING
%dir %{_datadir}/pkgconfig
%{_datadir}/pkgconfig/booth.pc

%description
Booth manages tickets which authorize cluster sites located
in geographically dispersed locations to run resources.
It facilitates support of geographically distributed
clustering in Pacemaker.

# SUBPACKAGES #

%package        core
Summary:        Booth core files (executables, etc.)
# for booth-keygen (chown, dd)
Requires:       coreutils
# deal with pre-split arrangement
Conflicts:      %{name} < 1.0-1

%description    core
Core files (executables, etc.) for Booth, ticket manager for
multi-site clusters.

%package        arbitrator
Summary:        Booth support for running as an arbitrator
BuildArch:      noarch
Requires:       %{name}-core = %{version}-%{release}
%{?systemd_requires}
# deal with pre-split arrangement
Conflicts:      %{name} < 1.0-1

%description    arbitrator
Support for running Booth, ticket manager for multi-site clusters,
as an arbitrator.

%post arbitrator
%systemd_post booth-arbitrator.service

%preun arbitrator
%systemd_preun booth-arbitrator.service

%postun arbitrator
%systemd_postun_with_restart booth-arbitrator.service

%package        site
Summary:        Booth support for running as a full-fledged site
BuildArch:      noarch
Requires:       %{name}-core = %{version}-%{release}
# for crm_{resource,simulate,ticket} utilities
Requires:       pacemaker >= 1.1.8
# for ocf-shellfuncs and other parts of OCF shell-based environment
Requires:       resource-agents
# deal with pre-split arrangement
Conflicts:      %{name} < 1.0-1

%description    site
Support for running Booth, ticket manager for multi-site clusters,
as a full-fledged site.

%package        test
Summary:        Test scripts for Booth
BuildArch:      noarch
# runtests.py suite (for hostname and killall respectively)
Requires:       hostname psmisc
# any of the following internal dependencies will pull -core package
## for booth@booth.service
Requires:       %{name}-arbitrator = %{version}-%{release}
## for booth-site and service-runnable scripts
## (and /usr/lib/ocf/resource.d/booth)
Requires:       %{name}-site = %{version}-%{release}
Requires:       gdb
Requires:       %{__python3}
%if 0%{?with_include_unit_test}
Requires:       python3-pexpect
%endif
# runtests.py suite (for perl and netstat)
Requires:       perl-interpreter net-tools

%description    test
Automated tests for running Booth, ticket manager for multi-site clusters.

# BUILD #

%prep
%autosetup -n %{name}-%{booth_sha1} -S git_am

%build
./autogen.sh
%{configure} \
        --with-initddir=%{_initrddir} \
        --docdir=%{_pkgdocdir} \
        --enable-user-flags \
        %{?with_html_man:--with-html_man} \
        %{!?with_glue:--without-glue} \
        PYTHON=%{__python3}
%{make_build}

%install
%{make_install}
mkdir -p %{buildroot}/%{_unitdir}
cp -a -t %{buildroot}/%{_unitdir} \
        -- conf/booth@.service conf/booth-arbitrator.service
install -D -m 644 -t %{buildroot}/%{_mandir}/man8 \
        -- docs/boothd.8
ln -s boothd.8 %{buildroot}/%{_mandir}/man8/booth.8
cp -a -t %{buildroot}/%{_pkgdocdir} \
        -- ChangeLog README-testing conf/booth.conf.example
# drop what we don't package anyway (COPYING added via tarball-relative path)
rm -rf %{buildroot}/%{_initrddir}/booth-arbitrator
rm -rf %{buildroot}/%{_pkgdocdir}/README.upgrade-from-v0.1
rm -rf %{buildroot}/%{_pkgdocdir}/COPYING
# tests
mkdir -p %{buildroot}/%{test_path}
# Copy tests from tarball
cp -a -t %{buildroot}/%{test_path} \
        -- conf test
%if 0%{?with_include_unit_test}
cp -a -t %{buildroot}/%{test_path} \
        -- unit-tests script/unit-test.py
%endif
chmod +x %{buildroot}/%{test_path}/test/booth_path
chmod +x %{buildroot}/%{test_path}/test/live_test.sh
mkdir -p %{buildroot}/%{test_path}/src
ln -s -t %{buildroot}/%{test_path}/src \
        -- %{_sbindir}/boothd
# Generate runtests.py and boothtestenv.py
sed -e 's#PYTHON_SHEBANG#%{__python3} -Es#g' \
    -e 's#TEST_SRC_DIR#%{test_path}/test#g' \
    -e 's#TEST_BUILD_DIR#%{test_path}/test#g' \
    %{buildroot}/%{test_path}/test/runtests.py.in > %{buildroot}/%{test_path}/test/runtests.py

chmod +x %{buildroot}/%{test_path}/test/runtests.py

sed -e 's#PYTHON_SHEBANG#%{__python3} -Es#g' \
    -e 's#TEST_SRC_DIR#%{test_path}/test#g' \
    -e 's#TEST_BUILD_DIR#%{test_path}/test#g' \
    %{buildroot}/%{test_path}/test/boothtestenv.py.in > %{buildroot}/%{test_path}/test/boothtestenv.py

# https://fedoraproject.org/wiki/Packaging:Python_Appendix#Manual_byte_compilation
%py_byte_compile %{__python3} %{buildroot}/%{test_path}

%check
# alternatively: test/runtests.py
%if 0%{?with_run_build_tests}
VERBOSE=1 make check
%endif

%files          core
%license COPYING
%doc %{_pkgdocdir}/AUTHORS
%doc %{_pkgdocdir}/ChangeLog
%doc %{_pkgdocdir}/README
%doc %{_pkgdocdir}/booth.conf.example
# core command(s) + man pages
%{_sbindir}/booth*
%{_mandir}/man8/booth*.8*
# configuration
%dir %{_sysconfdir}/booth
%exclude %{_sysconfdir}/booth/booth.conf.example

%dir %attr (750, %{uname}, %{gname}) %{_var}/lib/booth/
%dir %attr (750, %{uname}, %{gname}) %{_var}/lib/booth/cores

# Generated html docs
%if 0%{?with_html_man}
%{_pkgdocdir}/booth-keygen.8.html
%{_pkgdocdir}/boothd.8.html
%endif

%files          arbitrator
%{_unitdir}/booth@.service
%{_unitdir}/booth-arbitrator.service

%files          site
# OCF (agent + a helper)
## /usr/lib/ocf/resource.d/pacemaker provided by pacemaker
%{_usr}/lib/ocf/resource.d/pacemaker/booth-site
%dir %{_usr}/lib/ocf/lib/booth
     %{_usr}/lib/ocf/lib/booth/geo_attr.sh
# geostore (command + OCF agent)
%{_sbindir}/geostore
%{_mandir}/man8/geostore.8*
## /usr/lib/ocf/resource.d provided by resource-agents
%dir %{_usr}/lib/ocf/resource.d/booth
     %{_usr}/lib/ocf/resource.d/booth/geostore
# helper (possibly used in the configuration hook)
%dir %{_datadir}/booth
     %{_datadir}/booth/service-runnable

# Generated html docs
%if 0%{?with_html_man}
%{_pkgdocdir}/geostore.8.html
%endif

%files          test
%doc %{_pkgdocdir}/README-testing
# /usr/share/booth provided by -site
%{test_path}
# /usr/lib/ocf/resource.d/booth provided by -site
%{_usr}/lib/ocf/resource.d/booth/sharedrsc

%changelog
* Mon Nov 21 2022 Jan Friesse <jfriesse@redhat.com> - 1.0-283.1.9d4029a.git
- Resolves: rhbz#2135865

- Update to current snapshot (commit 9d4029a) (rhbz#2135865)

* Wed Aug 03 2022 Jan Friesse <jfriesse@redhat.com> - 1.0-199.2.ac1d34c.git
- Resolves: rhbz#2111668

- Fix authfile directive handling in booth config file
  (fixes CVE-2022-2553)
- Add enable-authfile option

* Thu Oct 15 2020 Jan Friesse <jfriesse@redhat.com> - 1.0-199.1.ac1d34c.git
- Resolves: rhbz#1873948
- Resolves: rhbz#1768172

- Fix versioning scheme to handle updates better
- Handle updated exit code of crm_ticket

* Wed Jun 3 2020 Jan Friesse <jfriesse@redhat.com> - 1.0-6.ac1d34c.git.2
- Related: rhbz#1835831

- Do not link with the pcmk libraries
- Generate runtests.py and boothtestenv.py with -Es as make check does

* Tue Jun 2 2020 Jan Friesse <jfriesse@redhat.com> - 1.0-6.ac1d34c.git.1
- Resolves: rhbz#1602455
- Resolves: rhbz#1682122
- Resolves: rhbz#1768369
- Resolves: rhbz#1835831

- Update to current snapshot (commit ac1d34c) to fix test suite,
  build warnings and build with gcc10
- Fix hardcoded-library-path
- Package /var/lib/booth where booth can chroot
- Add '?dist' macro to release field
- Pass full path of Python3 to configure
- Add CI tests
- Enable gating

* Wed Sep 19 2018 Tomas Orsava <torsava@redhat.com> - 1.0-5.f2d38ce.git
- Require the Python interpreter directly instead of using the package name
- Related: rhbz#1619153

* Thu Jul 19 2018 Jan Pokorný <jpokorny+rpm-booth@redhat.com> - 1.0-4.f2d38ce.git
- revert back to using asciidoc instead of asciidoctor for generating man pages
  (rhbz#1603119)
- fix some issues in the shell scripts (rhbz#1602455)

* Mon Jul 16 2018 Jan Pokorný <jpokorny+rpm-booth@redhat.com> - 1.0-3.f2d38ce.git
- update for another, current snapshot beyond booth-1.0
  (commit f2d38ce), including:
  . support for solely manually managed tickets (9a365f9)
  . use asciidoctor instead of asciidoc for generating man pages (65e6a6b)
- switch to using Python 3 for the tests instead of Python 2
  (behind unversioned "python" references; rhbz#1590856)

* Thu Jun 21 2018 Troy Dawson <tdawson@redhat.com> - 1.0-2.570876d.git.3
- Fix python shebangs (#1580601)

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.0-2.570876d.git.2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0-2.570876d.git.1
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Wed May 25 2016 Jan Pokorný <jpokorny+rpm-booth@fedoraproject.org> - 1.0-3.570876d.git
- update per the changesets recently accepted by the upstream
  (memory/resource leaks fixes, patches previously attached separately
  that make unit test pass, internal cleanups, etc.)

* Thu May 05 2016 Jan Pokorný <jpokorny+rpm-booth@fedoraproject.org> - 1.0-2.eb4256a.git
- update a subset of out-of-tree patches per
  https://github.com/ClusterLabs/booth/pull/22#issuecomment-216936987
- pre-inclusion cleanups in the spec (apply systemd scriptlet operations
  with booth-arbitrator, avoid overloading file implicitly considered %%doc
  as %%license)
  Resolves: rhbz#1314865
  Related: rhbz#1333509

* Thu Apr 28 2016 Jan Pokorný <jpokorny+rpm-booth@fedoraproject.org> - 1.0-1.eb4256a.git
- initial build
