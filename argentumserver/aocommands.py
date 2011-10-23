# -*- coding: utf-8 -*-

"""
    AONX Server - Pequeño servidor de Argentum Online.
    Copyright (C) 2011 Alejandro Santos <alejolp@alejolp.com.ar>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__all__ = ['CommandsDecoderException', 'CriticalDecoderException', \
    'ClientCommandsDecoder', 'ServerCommandsEncoder']

import time

from bytequeue import ByteQueue, ByteQueueError, ByteQueueInsufficientData
from aoprotocol import clientPackets, serverPackets, clientPacketsFlip
from util import debug_print
from gamerules import *
from player import Player
import aoprotocol, gamerules, constants, corevars

class CommandsDecoderException(Exception):
    """Faltan datos para decodificar un comando del cliente"""
    pass

class CriticalDecoderException(Exception):
    """Error critico en los datos del cliente; cerrar la conexion"""
    pass

class ClientCommandsDecoder(object):
    """Conjunto de funciones para decodificar los datos que envia un cliente"""

    def __init__(self):
        self.cmds = [None] * (aoprotocol.lastClientPacketID + 1)

        for cmdName, cmdId in clientPackets.items():
            self.cmds[cmdId] = getattr(self, "handleCmd" + cmdName, None)

        missingHandlers = [x for x in dir(self) if x.startswith("handleCmd") \
            and getattr(self, x) not in self.cmds]

        if len(missingHandlers) > 0:
            print "Error critico: handlers no utilizados: ", missingHandlers
            assert False

    def handleData(self, prot):
        buf = prot._ao_inbuff
        cmd = None

        """
        Los comandos consumen los bytes del buffer de entrada, si faltan
        datos se dispara un CommandsDecoderException o ByteQueueError.
        """

        try:
            try:
                while len(buf) > 0:
                    cmd = buf.peekInt8()

                    if cmd < 0 or cmd >= len(self.cmds):
                        debug_print("cmd out of range:", cmd)
                        raise CriticalDecoderException()

                    if self.cmds[cmd] is None:
                        debug_print("cmd not implemented:", cmd, \
                            "should be:", clientPacketsFlip.get(cmd, '?'))
                        raise CriticalDecoderException()

                    # Marca la posicion actual por si hay que hacer rollback.
                    buf.mark()

                    # Invoca al handler del comando cmd.
                    self.cmds[cmd](prot, buf)


                # La operacion commit() destruye los datos del buffer,
                # por lo que para llamarla tengo que estar seguro
                # que se leyeron todos los datos del comando actual.
                #
                # Llamarla al final de cada comando puede llegar a ser
                # lento si hay varios comandos encolados.

                buf.commit()

                prot.lastHandledPacket = time.time()

            except:
                buf.rollback()
                raise
        except ByteQueueError, e:
            pass
            debug_print("ByteQueueError", e)
        except ByteQueueInsufficientData, e:
            pass
        except CommandsDecoderException, e:
            pass
            # debug_print("CommandsDecoderException")
        except CriticalDecoderException, e:
            if cmd is not None:
                debug_print("CriticalDecoderException", cmd, \
                    clientPacketsFlip.get(cmd, '?'), e)
            raise
        except Exception, e:
            debug_print("handleData Exception: ", e)
            raise

    def CheckLogged(fOrig):
        """Decorator para verificar que el usuario esta logeado"""
        def fNew(self, prot, buf):
            if prot.player is None:
                raise CriticalDecoderException()
            return fOrig(self, prot, buf, prot.player)
        return fNew

    def CheckNotLogged(fOrig):
        """Decorator para verificar que el usuario no esta logeado"""
        def fNew(self, prot, buf):
            if prot.player is not None:
                raise CriticalDecoderException()
            return fOrig(self, prot, buf, None)
        return fNew

    @CheckNotLogged
    def handleCmdLoginExistingChar(self, prot, buf, player):
        # PacketID
        cmd = buf.readInt8()

        playerName = buf.readString()
        playerPass = buf.readString()
        playerVers = '%d.%d.%d' % (buf.readInt8(), buf.readInt8(),\
            buf.readInt8())

        error = False

        if not gamerules.isValidPlayerName(playerName, False):
            prot.cmdout.sendErrorMsg("Nombre invalido")
            error = True
            debug_print("Nombre invalido:", repr(playerName))
        elif corevars.gameServer.playersLimitReached():
            prot.cmdout.sendErrorMsg("Limite de jugadores alcanzado")
            error = True
        elif corevars.gameServer.isPlayerLogged(playerName):
            prot.cmdout.sendErrorMsg("El jugador ya se encuentra logeado")
            error = True
        else:
            # La instancia de Player se crea recien cuando es válido.
            prot.player = Player(prot, playerName)
            prot.player.start()

        if error:
            prot.loseConnection()

    @CheckNotLogged
    def handleCmdThrowDices(self, prot, buf, player):
        prot.cmdout.sendErrorMsg(constants.CREACION_PJS)
        raise CriticalDecoderException("Not Implemented")

    @CheckNotLogged
    def handleCmdLoginNewChar(self, prot, buf, player):
        prot.cmdout.sendErrorMsg(constants.CREACION_PJS)
        raise CriticalDecoderException("Not Implemented")

    @CheckLogged
    def handleCmdTalk(self, prot, buf, player):
        # PacketID
        cmd = buf.readInt8()
        msg = buf.readString()
        player.onTalk(msg, False)

    @CheckLogged
    def handleCmdWalk(self, prot, buf, player):
        cmd = buf.readInt8()
        heading = buf.readInt8()
        player.move(heading)

    @CheckLogged
    def handleCmdOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        player.cmdout.sendConsoleMsg(\
            "Online: %d" % corevars.gameServer.playersCount(), \
            constants.FONTTYPES['SERVER'])

    @CheckLogged
    def handleCmdQuit(self, prot, buf, player):
        cmd = buf.readInt8()
        player.quit()

    @CheckLogged
    def handleCmdYell(self, prot, buf, player):
        cmd = buf.readInt8()
        msg = buf.readString()
        player.onTalk(msg, True)

    @CheckLogged
    def handleCmdWhisper(self, prot, buf, player):
        cmd = buf.readInt8()
        target = buf.readInt16()
        msg = buf.readString()
        # FIXME

    @CheckLogged
    def handleCmdRequestPositionUpdate(self, prot, buf, player):
        cmd = buf.readInt8()
        player.sendPosUpdate()

    @CheckLogged
    def handleCmdAttack(self, prot, buf, player):
        cmd = buf.readInt8()
        player.doAttack()

    @CheckLogged
    def handleCmdPickUp(self, prot, buf, player):
        cmd = buf.readInt8()
        player.doPickUp()

    @CheckLogged
    def handleCmdSafeToggle(self, prot, buf, player):
        cmd = buf.readInt8()
        # FIXME

    @CheckLogged
    def handleCmdResuscitationSafeToggle(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestGuildLeaderInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestAtributes(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestFame(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestSkills(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestMiniStats(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceEnd(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceEnd(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceConfirm(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceChat(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankEnd(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceOk(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceReject(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdDrop(self, prot, buf, player):
        cmd = buf.readInt8()
        slot = buf.readInt8()
        amount = buf.readInt16()
        player.onDrop(slot, amount)

    @CheckLogged
    def handleCmdCastSpell(self, prot, buf, player):
        cmd = buf.readInt8()
        spellIdx = buf.readInt8()
        player.onCastSpell(spellIdx)

    @CheckLogged
    def handleCmdLeftClick(self, prot, buf, player):
        cmd = buf.readInt8()
        x, y = buf.readInt8(), buf.readInt8()
        player.onLookAtTile(x, y)

    @CheckLogged
    def handleCmdDoubleClick(self, prot, buf, player):
        cmd = buf.readInt8()
        x, y = buf.readInt8(), buf.readInt8()
        player.onDoubleClick(x, y)

    @CheckLogged
    def handleCmdWork(self, prot, buf, player):
        cmd = buf.readInt8()
        skill = buf.readInt8()
        player.onWork(skill)

    @CheckLogged
    def handleCmdUseSpellMacro(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUseItem(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCraftBlacksmith(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCraftCarpenter(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdWorkLeftClick(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCreateNewGuild(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdSpellInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdEquipItem(self, prot, buf, player):
        cmd = buf.readInt8()
        slot = buf.readInt8()
        player.onEquipItem(slot)

    @CheckLogged
    def handleCmdChangeHeading(self, prot, buf, player):
        cmd = buf.readInt8()
        heading = buf.readInt8()
        
        if heading < 1 or heading > 4:
            raise CriticalDecoderException('Invalid heading')

        player.heading = heading
        player.onCharacterChange()

    @CheckLogged
    def handleCmdModifySkills(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdTrain(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceBuy(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankExtractItem(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceSell(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankDeposit(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdForumPost(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdMoveSpell(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdMoveBank(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdClanCodexUpdate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUserCommerceOffer(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAcceptPeace(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRejectAlliance(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRejectPeace(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAcceptAlliance(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOfferPeace(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOfferAlliance(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAllianceDetails(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildPeaceDetails(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRequestJoinerInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAlliancePropList(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildPeacePropList(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildDeclareWar(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildNewWebsite(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildAcceptNewMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRejectNewMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildKickMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildUpdateNews(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildMemberInfo(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOpenElections(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRequestMembership(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildRequestDetails(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildLeave(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestAccountState(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPetStand(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPetFollow(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdReleasePet(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdTrainList(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRest(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdMeditate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdResucitate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdHeal(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdHelp(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestStats(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCommerceStart(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankStart(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdEnlist(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInformation(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdReward(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestMOTD(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdUpTime(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyLeave(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyCreate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyJoin(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInquiry(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildMessage(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyMessage(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCentinelReport(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyOnline(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdCouncilMessage(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRoleMasterRequest(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGMRequest(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdbugReport(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdChangeDescription(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildVote(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPunishments(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdChangePassword(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGamble(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInquiryVote(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdLeaveFaction(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankExtractGold(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdBankDepositGold(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdDenounce(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildFundate(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGuildFundation(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyKick(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartySetLeader(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPartyAcceptMember(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdPing(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdRequestPartyForm(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdItemUpgrade(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdGMCommands(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdInitCrafting(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdHome(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdShowGuildNews(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdShareNpc(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdStopSharingNpc(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

    @CheckLogged
    def handleCmdConsultation(self, prot, buf, player):
        cmd = buf.readInt8()
        raise CriticalDecoderException('Not Implemented')
        # FIXME

class ServerCommandsEncoder(object):
    """
    Conjunto de funciones para generar comandos hacia el cliente.

    Es un Wrapper afuera de AoProtocol.
    """

    __slots__ = ('buf', 'prot', )

    def __init__(self, prot):
        self.buf = prot.outbuf
        self.prot = prot # K-Pax.

    def sendConsoleMsg(self, msg, font):
        self.buf.writeInt8(serverPackets['ConsoleMsg'])
        self.buf.writeString(msg)
        self.buf.writeInt8(font)
        self.prot.flushOutBuf()

    def sendLogged(self, userClass):
        self.buf.writeInt8(serverPackets['Logged'])
        self.buf.writeInt8(userClass)
        self.prot.flushOutBuf()

    def sendChangeMap(self, mapNum, vers):
        self.buf.writeInt8(serverPackets['ChangeMap'])
        self.buf.writeInt16(mapNum)
        self.buf.writeInt16(vers)
        self.prot.flushOutBuf()

    def sendUserIndexInServer(self, idx):
        self.buf.writeInt8(serverPackets['UserIndexInServer'])
        self.buf.writeInt16(idx)
        self.prot.flushOutBuf()

    def sendUserCharIndexInServer(self, idx):
        self.buf.writeInt8(serverPackets['UserCharIndexInServer'])
        self.buf.writeInt16(idx)
        self.prot.flushOutBuf()

    def sendRemoveDialogs(self):
        self.buf.writeInt8(serverPackets['RemoveDialogs'])
        self.prot.flushOutBuf()

    def sendRemoveCharDialog(self, chridx):
        self.buf.writeInt8(serverPackets['RemoveCharDialog'])
        self.buf.writeInt16(chridx)
        self.prot.flushOutBuf()

    def sendNavigateToggle(self):
        self.buf.writeInt8(serverPackets['NavigateToggle'])
        self.prot.flushOutBuf()

    def sendDisconnect(self):
        self.buf.writeInt8(serverPackets['Disconnect'])
        self.prot.flushOutBuf()

    def sendCommerceEnd(self):
        self.buf.writeInt8(serverPackets['CommerceEnd'])
        self.prot.flushOutBuf()

    def sendBankEnd(self):
        self.buf.writeInt8(serverPackets['BankEnd'])
        self.prot.flushOutBuf()

    def sendCommerceInit(self):
        self.buf.writeInt8(serverPackets['CommerceInit'])
        self.prot.flushOutBuf()

    def sendBankInit(self):
        self.buf.writeInt8(serverPackets['BankInit'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUserCommerceInit(self):
        self.buf.writeInt8(serverPackets['UserCommerceInit'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUserCommerceEnd(self):
        self.buf.writeInt8(serverPackets['UserCommerceEnd'])
        self.prot.flushOutBuf()

    def sendUserOfferConfirm(self):
        self.buf.writeInt8(serverPackets['UserOfferConfirm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendCommerceChat(self, chat, font):
        self.buf.writeInt8(serverPackets['CommerceChat'])
        self.buf.writeString(chat)
        self.buf.writeInt8(font)
        self.prot.flushOutBuf()

    def sendShowBlacksmithForm(self):
        self.buf.writeInt8(serverPackets['ShowBlacksmithForm'])
        self.prot.flushOutBuf()

    def sendShowCarpenterForm(self):
        self.buf.writeInt8(serverPackets['ShowCarpenterForm'])
        self.prot.flushOutBuf()

    def sendUpdateSta(self, sta):
        self.buf.writeInt8(serverPackets['UpdateSta'])
        self.buf.writeInt16(sta)
        self.prot.flushOutBuf()

    def sendUpdateMana(self, mana):
        self.buf.writeInt8(serverPackets['UpdateMana'])
        self.buf.writeInt16(mana)
        self.prot.flushOutBuf()

    def sendUpdateHP(self, hp):
        self.buf.writeInt8(serverPackets['UpdateHP'])
        self.buf.writeInt16(hp)
        self.prot.flushOutBuf()

    def sendUpdateGold(self, gld):
        self.buf.writeInt8(serverPackets['UpdateGold'])
        self.buf.writeInt32(gld)
        self.prot.flushOutBuf()

    def sendUpdateBankGold(self, gld):
        self.buf.writeInt8(serverPackets['UpdateBankGold'])
        self.buf.writeInt32(gld)
        self.prot.flushOutBuf()

    def sendUpdateExp(self, exp):
        self.buf.writeInt8(serverPackets['UpdateExp'])
        self.buf.writeInt32(exp)
        self.prot.flushOutBuf()

    def sendPosUpdate(self, x, y):
        self.buf.writeInt8(serverPackets['PosUpdate'])
        self.buf.writeInt8(x)
        self.buf.writeInt8(y)
        self.prot.flushOutBuf()

    def sendChatOverHead(self, chat, chridx, color):
        self.buf.writeInt8(serverPackets['ChatOverHead'])
        self.buf.writeString(chat)
        self.buf.writeInt16(chridx)

        self.buf.writeInt8(color & 0xff)
        self.buf.writeInt8((color >> 8) & 0xff)
        self.buf.writeInt8((color >> 16) & 0xff)

        self.prot.flushOutBuf()

    def sendGuildChat(self, msg):
        self.buf.writeInt8(serverPackets['GuildChat'])
        self.buf.writeString(msg)
        self.prot.flushOutBuf()

    def sendShowMessageBox(self, msg):
        self.buf.writeInt8(serverPackets['ShowMessageBox'])
        self.buf.writeString(msg)
        self.prot.flushOutBuf()

    def sendCharacterCreate(self, chridx, body, head, heading, x, y, weapon, shield, helmet, fx, fxloops, name, nickColor, priv):
        self.buf.writeInt8(serverPackets['CharacterCreate'])
        self.buf.writeInt16(chridx)
        self.buf.writeInt16(body)
        self.buf.writeInt16(head)
        self.buf.writeInt8(heading)
        self.buf.writeInt8(x)
        self.buf.writeInt8(y)
        self.buf.writeInt16(weapon)
        self.buf.writeInt16(shield)
        self.buf.writeInt16(helmet)
        self.buf.writeInt16(fx)
        self.buf.writeInt16(fxloops)
        self.buf.writeString(name)
        self.buf.writeInt8(nickColor)
        self.buf.writeInt8(priv)
        self.prot.flushOutBuf()

    def sendCharacterRemove(self, chridx):
        self.buf.writeInt8(serverPackets['CharacterRemove'])
        self.buf.writeInt16(chridx)
        self.prot.flushOutBuf()

    def sendCharacterChangeNick(self, chridx, nick):
        self.buf.writeInt8(serverPackets['CharacterChangeNick'])
        self.buf.writeInt16(chridx)
        self.buf.writeString(nick)
        self.prot.flushOutBuf()

    def sendCharacterMove(self, chridx, x, y):
        self.buf.writeInt8(serverPackets['CharacterMove'])
        self.buf.writeInt16(chridx)
        self.buf.writeInt8(x)
        self.buf.writeInt8(y)
        self.prot.flushOutBuf()

    def sendForceCharMove(self, heading):
        self.buf.writeInt8(serverPackets['ForceCharMove'])
        self.buf.writeInt8(heading)
        self.prot.flushOutBuf()

    def sendCharacterChange(self, chridx, body, head, heading, weapon, shield, helmet, fx, fxloops):
        self.buf.writeInt8(serverPackets['CharacterChange'])
        self.buf.writeInt16(chridx)
        self.buf.writeInt16(body)
        self.buf.writeInt16(head)
        self.buf.writeInt8(heading)
        self.buf.writeInt16(weapon)
        self.buf.writeInt16(shield)
        self.buf.writeInt16(helmet)
        self.buf.writeInt16(fx)
        self.buf.writeInt16(fxloops)
        self.prot.flushOutBuf()

    def sendObjectCreate(self, x, y, grhIdx):
        self.buf.writeInt8(serverPackets['ObjectCreate'])
        self.buf.writeInt8(x)
        self.buf.writeInt8(y)
        self.buf.writeInt16(grhIdx)
        self.prot.flushOutBuf()

    def sendObjectDelete(self, x, y):
        self.buf.writeInt8(serverPackets['ObjectDelete'])
        self.buf.writeInt8(x)
        self.buf.writeInt8(y)
        self.prot.flushOutBuf()

    def sendBlockPosition(self, x, y, b):
        self.buf.writeInt8(serverPackets['BlockPosition'])
        for q in [x, y, b]:
            self.writeInt8(q)
        self.prot.flushOutBuf()

    def sendPlayMidi(self):
        self.buf.writeInt8(serverPackets['PlayMidi'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendPlayWave(self):
        self.buf.writeInt8(serverPackets['PlayWave'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendguildList(self):
        self.buf.writeInt8(serverPackets['guildList'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendAreaChanged(self):
        self.buf.writeInt8(serverPackets['AreaChanged'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendPauseToggle(self):
        self.buf.writeInt8(serverPackets['PauseToggle'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendRainToggle(self):
        self.buf.writeInt8(serverPackets['RainToggle'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendCreateFX(self, fx, fxloops, chridx):
        self.buf.writeInt8(serverPackets['CreateFX'])
        for x in [fx, fxloops, chridx]:
            self.buf.writeInt16(x)
        self.prot.flushOutBuf()

    def sendUpdateUserStats(self, hpMax, hp, manMax, man, staMax, sta, gld, elv, elu, exp):
        self.buf.writeInt8(serverPackets['UpdateUserStats'])
        for x in [hpMax, hp, manMax, man, staMax, sta]:
            self.buf.writeInt16(x)
        self.buf.writeInt32(gld)
        self.buf.writeInt8(elv)
        self.buf.writeInt32(elu)
        self.buf.writeInt32(exp)
        self.prot.flushOutBuf()

    def sendWorkRequestTarget(self):
        self.buf.writeInt8(serverPackets['WorkRequestTarget'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendChangeInventorySlot(self, slot, objIdx, name, amount, equipped, grhIdx, objType, hitMax, hit, defMax, defMin, price):
        self.buf.writeInt8(serverPackets['ChangeInventorySlot'])
        self.buf.writeInt16(objIdx)
        self.buf.writeString(name)
        self.buf.writeInt16(amount)
        self.buf.writeBoolean(equipped)
        self.buf.writeInt16(grhIdx)
        self.buf.writeInt16(objType)
        for x in [hitMax, hit, defMax, defMin]:
            self.buf.writeInt16(x)
        self.buf.writeSingle(price)
        self.prot.flushOutBuf()

    def sendChangeBankSlot(self):
        self.buf.writeInt8(serverPackets['ChangeBankSlot'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendChangeSpellSlot(self, slot, spellIdx, name):
        self.buf.writeInt8(serverPackets['ChangeSpellSlot'])
        self.buf.writeInt8(slot)
        self.buf.writeInt16(spellIdx)
        self.buf.writeString(name)
        self.prot.flushOutBuf()

    def sendAtributes(self):
        self.buf.writeInt8(serverPackets['Atributes'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendBlacksmithWeapons(self):
        self.buf.writeInt8(serverPackets['BlacksmithWeapons'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendBlacksmithArmors(self):
        self.buf.writeInt8(serverPackets['BlacksmithArmors'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendCarpenterObjects(self):
        self.buf.writeInt8(serverPackets['CarpenterObjects'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendRestOK(self):
        self.buf.writeInt8(serverPackets['RestOK'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendErrorMsg(self, msg):
        self.buf.writeInt8(serverPackets['ErrorMsg'])
        self.buf.writeString(msg)
        self.prot.flushOutBuf()

    def sendBlind(self):
        self.buf.writeInt8(serverPackets['Blind'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendDumb(self):
        self.buf.writeInt8(serverPackets['Dumb'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowSignal(self):
        self.buf.writeInt8(serverPackets['ShowSignal'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendChangeNPCInventorySlot(self):
        self.buf.writeInt8(serverPackets['ChangeNPCInventorySlot'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUpdateHungerAndThirst(self, aguMax, agu, hamMax, ham):
        self.buf.writeInt8(serverPackets['UpdateHungerAndThirst'])
        for x in [aguMax, agu, hamMax, ham]:
            self.buf.writeInt8(x)
        self.prot.flushOutBuf()

    def sendFame(self):
        self.buf.writeInt8(serverPackets['Fame'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendMiniStats(self):
        self.buf.writeInt8(serverPackets['MiniStats'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendLevelUp(self):
        self.buf.writeInt8(serverPackets['LevelUp'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendAddForumMsg(self):
        self.buf.writeInt8(serverPackets['AddForumMsg'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowForumForm(self):
        self.buf.writeInt8(serverPackets['ShowForumForm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendSetInvisible(self):
        self.buf.writeInt8(serverPackets['SetInvisible'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendDiceRoll(self):
        self.buf.writeInt8(serverPackets['DiceRoll'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendMeditateToggle(self):
        self.buf.writeInt8(serverPackets['MeditateToggle'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendBlindNoMore(self):
        self.buf.writeInt8(serverPackets['BlindNoMore'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendDumbNoMore(self):
        self.buf.writeInt8(serverPackets['DumbNoMore'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendSendSkills(self, userSkills, expSkills):
        self.buf.writeInt8(serverPackets['SendSkills'])

        if len(userSkills) != constants.NUMSKILLS:
            raise TypeError()
        if len(expSkills) != constants.NUMSKILLS:
            raise TypeError()

        for a, b in zip(userSkills, expSkills):
            self.buf.writeInt8(a)
            self.buf.writeInt8(b)
        self.prot.flushOutBuf()

    def sendTrainerCreatureList(self):
        self.buf.writeInt8(serverPackets['TrainerCreatureList'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendguildNews(self):
        self.buf.writeInt8(serverPackets['guildNews'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendOfferDetails(self):
        self.buf.writeInt8(serverPackets['OfferDetails'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendAlianceProposalsList(self):
        self.buf.writeInt8(serverPackets['AlianceProposalsList'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendPeaceProposalsList(self):
        self.buf.writeInt8(serverPackets['PeaceProposalsList'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendCharacterInfo(self):
        self.buf.writeInt8(serverPackets['CharacterInfo'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendGuildLeaderInfo(self):
        self.buf.writeInt8(serverPackets['GuildLeaderInfo'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendGuildMemberInfo(self):
        self.buf.writeInt8(serverPackets['GuildMemberInfo'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendGuildDetails(self):
        self.buf.writeInt8(serverPackets['GuildDetails'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowGuildFundationForm(self):
        self.buf.writeInt8(serverPackets['ShowGuildFundationForm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendParalizeOK(self):
        self.buf.writeInt8(serverPackets['ParalizeOK'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowUserRequest(self):
        self.buf.writeInt8(serverPackets['ShowUserRequest'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendTradeOK(self):
        self.buf.writeInt8(serverPackets['TradeOK'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendBankOK(self):
        self.buf.writeInt8(serverPackets['BankOK'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendChangeUserTradeSlot(self):
        self.buf.writeInt8(serverPackets['ChangeUserTradeSlot'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendSendNight(self):
        self.buf.writeInt8(serverPackets['SendNight'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendPong(self):
        self.buf.writeInt8(serverPackets['Pong'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUpdateTagAndStatus(self):
        self.buf.writeInt8(serverPackets['UpdateTagAndStatus'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendSpawnList(self):
        self.buf.writeInt8(serverPackets['SpawnList'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowSOSForm(self):
        self.buf.writeInt8(serverPackets['ShowSOSForm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowMOTDEditionForm(self):
        self.buf.writeInt8(serverPackets['ShowMOTDEditionForm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowGMPanelForm(self):
        self.buf.writeInt8(serverPackets['ShowGMPanelForm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUserNameList(self):
        self.buf.writeInt8(serverPackets['UserNameList'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowGuildAlign(self):
        self.buf.writeInt8(serverPackets['ShowGuildAlign'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendShowPartyForm(self):
        self.buf.writeInt8(serverPackets['ShowPartyForm'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUpdateStrenghtAndDexterity(self):
        self.buf.writeInt8(serverPackets['UpdateStrenghtAndDexterity'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUpdateStrenght(self):
        self.buf.writeInt8(serverPackets['UpdateStrenght'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendUpdateDexterity(self):
        self.buf.writeInt8(serverPackets['UpdateDexterity'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendAddSlots(self):
        self.buf.writeInt8(serverPackets['AddSlots'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendMultiMessage(self):
        self.buf.writeInt8(serverPackets['MultiMessage'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

    def sendStopWorking(self):
        self.buf.writeInt8(serverPackets['StopWorking'])
        self.prot.flushOutBuf()

    def sendCancelOfferItem(self):
        self.buf.writeInt8(serverPackets['CancelOfferItem'])
        raise CriticalDecoderException('Not Implemented')
        # FIXME

        self.prot.flushOutBuf()

