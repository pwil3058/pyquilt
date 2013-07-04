QUILT_BASE_DIR=$(HOME)/XSRC/GIT/quilt
QUILTTESTDIR=$(QUILT_BASE_DIR)/test
TESTDIR=quilt-test
QUILTTESTS :=	$(filter-out $(QUILTTESTDIR)/patch-wrapper.test,$(wildcard $(QUILTTESTDIR)/*.test))
TESTS := $(patsubst $(QUILTTESTDIR)/%.test, $(TESTDIR)/%.test, $(QUILTTESTS))
DIRT +=		$(wildcard $(TESTDIR)/.*.ok)

# Settings for running the uninstalled version of pyquilt in the source tree:
PATH :=		$(CURDIR):$(PATH)
QUILTRC :=	$(QUILTTESTDIR)/test.quiltrc
export QUILTRC
CHECKRUN=$(QUILTTESTDIR)/run

#-----------------------------------------------------------------------

check: $(TESTDIR) $(TESTS) $(QUILTRC) $(TESTS:$(TESTDIR)/%.test=$(TESTDIR)/.%.ok)

check-% : $(TESTDIR)/.%.ok
	@/bin/true

$(TESTDIR):
	mkdir $(TESTDIR) 2> /dev/null

$(TESTDIR)/delete.test: $(QUILTTESTDIR)/delete.test
	sed -e "s/$$ *quilt/$$ pyquilt/" -e "s/find: \`?\./dir'?: Permission denied/.pc/test3/dir: Permission denied/" < $^ > $@

$(TESTDIR)/%.test: $(QUILTTESTDIR)/%.test
	sed -e "s/$$ *quilt/$$ pyquilt/" < $^ > $@

ifneq ($(shell . $(QUILTRC) ;  echo $$QUILT_PATCHES_PREFIX),)
CHECK_ENV := P=patches/; _P=../patches/; export P _P
endif

$(TESTDIR)/.%.ok : $(TESTDIR)/%.test
	@LANG=C; LC_ALL=C;						\
	export LANG LC_ALL;						\
	$(CHECK_ENV);							\
	cd $(@D);							\
	export QUILT_DIR=$(QUILT_BASE_DIR)/quilt;	\
	$(QUILTTESTDIR)/run -q $(<F)
	@touch $@

clean :
	rm -f $(DIRT)
	rm -f pyquilt_pkg/*.pyc

spotless:
	rm -fr $(TESTDIR)
	rm -f pyquilt_pkg/*.pyc pyquilt_pkg/*.orig

