from launcher_utils import *
from defensics_config import *


def suite_specific_cmd(chosen_suite):
    cmd = []
    if chosen_suite == 'btle-ad':
        cmd = ['--min-adv-interval', min_adv_intrvl_adv, '--max-adv-interval', max_adv_intrvl_adv]
        return cmd
    elif chosen_suite == 'btle-attc':
        cmd = [
            '--local-name', local_name_att,
            '--first-input-timeout', first_input_timeout,
            '--delay-before-disconnect', delay_before_disconnect,
            '--io-capability', io_capability_att,
            '--passkey', passkey_att,
            '--min-adv-interval', min_adv_intrvl_att,
            '--max-adv-interval', max_adv_intrvl_att,
            '--read-handle', read_handle,
            '--write-handle', write_handle
        ] + ['--keep-link' if keep_link_att else '--no-keep-link']
        return cmd
    elif chosen_suite == 'btle-att':
        cmd = [
            '--host-addr', host_addr,
            '--addr-type', addr_type,
            '--local-name', local_name_att_sr,
        ] + \
            ['--follow-resolvable' if follow_rpa else '--dont-follow-resolvable'] + \
            ['--keep-link' if keep_link_att_sr else '--no-keep-link'] + \
            ['--supervision-timeout-failure' if supervision_timeout_failure else '--no-supervision-timeout-failure'] + \
            ['--enable-att-server' if enable_att_sr else '--disable-att-server'] + \
            ['--enable-pairing' if pair_devices else '--no-enable-pairing'] + \
            ['--passkey' if pair_devices else ''] + \
            ['--passkey' if pair_devices else '']
        return cmd
    elif chosen_suite == 'btle-hogp':
        cmd = [
            '--local-name', local_name_hogp,
            '--io-capability', io_capability_hogp,
        ] + \
            ['--require-mitm' if require_mitm else '--no-require-mitm'] + \
            ['--require-bonding' if require_bonding else '--no-require-bonding']
        return cmd
    elif chosen_suite == 'btle-smpc':
        cmd = [
            '--local-name', local_name_smp,
            '--uuid', uuid,
            '--passkey', passkey_smp
        ] + \
            ['--keep-link' if keep_link_smp else '--no-keep-link'] + \
            ['--enable-att-server' if enable_att_sr_smp else '--disable-att-server'] + \
            ['--bonding' if bonding else '--no-bonding']
        return cmd
    elif chosen_suite == 'coap-server':
        cmd = [
            '--to-uri', coap_host_and_port,
            '--source-port', coap_sending_port
        ] + \
            ['--reuse-sctp' if reuse_tcp else '']
        return cmd
    else:
        return ['']


cmds = [
    ['java', '-jar', monitor_path] +
    ['--selection-mode' if test_indices == '' else '', selection_mode if test_indices == '' else ''] +
    ['--trim-percent'if selection_mode == 'trim' and test_indices == '' else '', \
     trim_percent if selection_mode == 'trim' and test_indices == '' else ''] +
    ['--verbose' if debug_info else []] + 
    ['--exec-after-test-run', after_run()] + 
    ['--suite', suite_path] + 
    ['--log-dir', results_path + folder_name + test_code] + 
    ['--no-loop'] + 
    ['--exec-test-run'] + instrumentation_external(before_run) + 
    ['--exec-pre-test-case'] + instrumentation_external(before_case) + 
    ['--exec-instrument'] + instrumentation_external(as_instrumentation) +
    ['--exec-post-test-case'] + instrumentation_external(after_each) + 
    ['--exec-instrument-fail'] + instrumentation_external(instrument_fail) +
    indices(test_indices)
]
cmds = cmds[0]

# suite specific commands
suite_cmds = suite_specific_cmd(suite_type)

complete_cmd = cmds + suite_cmds

server_process, server_log = server_run()
btmon_process = btmon_run(btmon_logs_name)
defensics_process, defensics_log = defensics_run(complete_cmd)

if isinstance(defensics_process.wait(), int):
    print('Defensics finished with returncode', defensics_process.poll())
    btmon_process.terminate()
    server_process.terminate()
